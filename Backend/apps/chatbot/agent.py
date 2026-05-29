"""
apps/chatbot/agent.py
=====================
LangGraph StateGraph definition for the BreatheESG Text-to-SQL agent.

Graph topology:
  START
    → intent_classifier
        → schema_retriever       (if intent = data_query)
        → response_formatter     (if intent = row_explanation / report_generation / clarify)
  schema_retriever
    → sql_generator
  sql_generator
    → sql_validator_node
  sql_validator_node
    → sql_executor               (if SQL is valid)
    → sql_generator              (if invalid AND retry_count < 3)
    → response_formatter         (if invalid AND retry_count >= 3)
  sql_executor
    → response_formatter         (if success or exhausted retries)
    → sql_generator              (if DB error AND retry_count < 2)
  response_formatter
    → output_classifier
  output_classifier
    → END

State is fully typed via AgentState TypedDict.
The compiled graph is a module-level singleton (thread-safe for Django).
"""

from typing import Optional, Annotated
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

from .nodes import (
    intent_classifier,
    schema_retriever,
    sql_generator,
    sql_validator_node,
    sql_executor,
    response_formatter,
    output_classifier,
)


# ── Agent State ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    """
    Full state object passed between all nodes in the LangGraph graph.

    All fields are optional except tenant_id and user_role which are
    always set by the view before invoking the graph.
    """
    # LangChain message history (uses add_messages reducer for append semantics)
    messages: Annotated[list[BaseMessage], add_messages]

    # Auth context — set once by the view, never modified by nodes
    tenant_id:  str
    user_role:  str

    # Node outputs — updated as graph progresses
    intent:          Optional[str]        # data_query | row_explanation | report_generation | clarify
    relevant_tables: Optional[list]       # tables identified by schema_retriever
    schema_context:  Optional[str]        # compact schema string for SQL generator
    generated_sql:   Optional[str]        # SQL from generator (may be secured by validator)
    sql_params:      list                 # bind parameters ([tenant_id, ...])
    query_result:    Optional[list]       # list of dicts from DB
    no_results:      bool                 # True if query returned 0 rows
    total_row_count: int                  # actual total rows (before LLM cap)
    truncated:       bool                 # True if results were capped at 200
    execution_time_ms: int               # DB execution time

    # Response fields — set by response_formatter + output_classifier
    answer:               str
    suggested_follow_ups: list
    response_type:        str            # text | table | chart | clarify
    chart_config:         Optional[dict]

    # Error + retry loop
    error:       Optional[str]
    retry_count: int

    # Context row (optional — for row_explanation from dashboard)
    context_row_id:     Optional[str]
    context_row_source: Optional[str]

    # Multi-turn conversation history (raw dicts, not LangChain messages)
    conversation_history: list


# ── Edge routing functions ────────────────────────────────────────────────────

def _route_after_intent(state: AgentState) -> str:
    """
    Route from intent_classifier:
    - data_query → schema_retriever (needs SQL path)
    - everything else → response_formatter (direct answer)
    """
    intent = state.get('intent', 'clarify')
    if intent == 'data_query':
        return 'schema_retriever'
    return 'response_formatter'


def _route_after_validator(state: AgentState) -> str:
    """
    Route from sql_validator_node:
    - Valid SQL   → sql_executor
    - Invalid SQL, retry_count < 3  → sql_generator (retry)
    - Invalid SQL, retry_count >= 3 → response_formatter (give up)
    """
    if state.get('error'):
        if state.get('retry_count', 0) < 3:
            return 'sql_generator'
        return 'response_formatter'
    return 'sql_executor'


def _route_after_executor(state: AgentState) -> str:
    """
    Route from sql_executor:
    - DB error, retry_count < 2 → sql_generator (retry with DB error context)
    - Success or exhausted      → response_formatter
    """
    if state.get('error') and state.get('retry_count', 0) < 2:
        return 'sql_generator'
    return 'response_formatter'


# ── Graph construction ────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    """Build and compile the LangGraph StateGraph."""
    graph = StateGraph(AgentState)

    # Register all nodes
    graph.add_node('intent_classifier',   intent_classifier)
    graph.add_node('schema_retriever',    schema_retriever)
    graph.add_node('sql_generator',       sql_generator)
    graph.add_node('sql_validator_node',  sql_validator_node)
    graph.add_node('sql_executor',        sql_executor)
    graph.add_node('response_formatter',  response_formatter)
    graph.add_node('output_classifier',   output_classifier)

    # Fixed edges
    graph.add_edge(START,                  'intent_classifier')
    graph.add_edge('schema_retriever',     'sql_generator')
    graph.add_edge('sql_generator',        'sql_validator_node')
    graph.add_edge('response_formatter',   'output_classifier')
    graph.add_edge('output_classifier',    END)

    # Conditional edges
    graph.add_conditional_edges(
        'intent_classifier',
        _route_after_intent,
        {
            'schema_retriever':   'schema_retriever',
            'response_formatter': 'response_formatter',
        },
    )
    graph.add_conditional_edges(
        'sql_validator_node',
        _route_after_validator,
        {
            'sql_executor':       'sql_executor',
            'sql_generator':      'sql_generator',
            'response_formatter': 'response_formatter',
        },
    )
    graph.add_conditional_edges(
        'sql_executor',
        _route_after_executor,
        {
            'sql_generator':      'sql_generator',
            'response_formatter': 'response_formatter',
        },
    )

    return graph.compile()


# ── Module-level compiled graph (singleton) ───────────────────────────────────
# Compiled once at import time. Thread-safe — LangGraph compiled graphs
# are stateless; all mutable state lives in the AgentState dict passed to invoke().
chatbot_graph = _build_graph()


def run_agent(initial_state: dict) -> dict:
    """
    Convenience function to invoke the compiled graph.

    Args:
        initial_state: Dict matching AgentState fields. Must contain
                       tenant_id, user_role, and at least one HumanMessage.

    Returns:
        Final AgentState dict after graph execution completes.
    """
    # Set default values for all optional state fields
    defaults = {
        'intent':               None,
        'relevant_tables':      [],
        'schema_context':       None,
        'generated_sql':        None,
        'sql_params':           [],
        'query_result':         None,
        'no_results':           False,
        'total_row_count':      0,
        'truncated':            False,
        'execution_time_ms':    0,
        'answer':               '',
        'suggested_follow_ups': [],
        'response_type':        'text',
        'chart_config':         None,
        'error':                None,
        'retry_count':          0,
        'context_row_id':       None,
        'context_row_source':   None,
        'conversation_history': [],
    }
    defaults.update(initial_state)
    return chatbot_graph.invoke(defaults)
