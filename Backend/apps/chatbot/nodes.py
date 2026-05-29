"""
apps/chatbot/nodes.py
=====================
All 7 LangGraph node functions for the BreatheESG chatbot agent.

Node execution order:
  intent_classifier → schema_retriever → sql_generator →
  sql_validator_node → sql_executor → response_formatter →
  output_classifier

Each node receives the full AgentState dict and returns a dict
of keys to update in the state. Nodes must NOT raise exceptions —
they catch internally and set state["error"].

Stateless design: no module-level mutable state. The LLM client
is instantiated once at module load (thread-safe).
"""

import json
import logging
import re
from typing import Any

from django.conf import settings
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from .prompts import (
    SYSTEM_PROMPT_INTENT_CLASSIFIER,
    SYSTEM_PROMPT_SQL_GENERATOR,
    SYSTEM_PROMPT_RESPONSE_FORMATTER,
    SYSTEM_PROMPT_SCHEMA_SELECTOR,
    QUERYABLE_TABLES,
    _get_india_fy_context,
)
from .safety import validate_and_secure_sql
from .tools import (
    execute_sql,
    build_schema_string,
    get_row_with_audit,
    identify_relevant_tables,
)

logger = logging.getLogger(__name__)

# ── LLM client (instantiated once at import time — thread-safe) ───────────────
_llm = ChatGoogleGenerativeAI(
    model=getattr(settings, 'CHATBOT_MODEL', 'gemini-2.0-flash'),
    max_tokens=getattr(settings, 'CHATBOT_MAX_TOKENS', 1000),
    api_key=getattr(settings, 'GEMINI_API_KEY', ''),
)

# Separate higher-token instance for response formatting (needs room for data)
_llm_formatter = ChatGoogleGenerativeAI(
    model=getattr(settings, 'CHATBOT_MODEL', 'gemini-2.0-flash'),
    max_tokens=2000,
    api_key=getattr(settings, 'GEMINI_API_KEY', ''),
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user_query(state: dict) -> str:
    """Extract the latest user message text from state messages."""
    messages = state.get('messages', [])
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            return msg.content
        if isinstance(msg, dict) and msg.get('role') == 'user':
            return msg.get('content', '')
    return ''


def _call_llm(system_prompt: str, user_content: str, use_formatter: bool = False) -> str:
    """
    Call the LLM with system + user messages. Returns the text response.
    Falls back to empty string on error (caller handles).
    """
    try:
        llm = _llm_formatter if use_formatter else _llm
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_content),
        ])
        return response.content.strip()
    except Exception as exc:
        logger.exception("LLM call failed: %s", exc)
        return ''


def _extract_json(text: str) -> dict:
    """
    Extract and parse the first JSON object from a text string.
    Handles LLM responses that wrap JSON in prose.
    """
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Find first {...} block
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return {}


# ── Node 1: Intent Classifier ─────────────────────────────────────────────────

def intent_classifier(state: dict) -> dict:
    """
    Classify the user's query into one of:
      data_query, row_explanation, report_generation, clarify

    Sets state["intent"]. If confidence < 0.70 or LLM fails, falls back to "clarify".

    State reads:  messages, context_row_id
    State writes: intent, error
    """
    user_query = _get_user_query(state)

    # If context_row_id is present, this is always row_explanation
    if state.get('context_row_id'):
        logger.info("intent=row_explanation (context_row_id present)")
        return {'intent': 'row_explanation', 'error': None}

    if not user_query:
        return {'intent': 'clarify', 'error': 'No query provided.'}

    try:
        raw = _call_llm(SYSTEM_PROMPT_INTENT_CLASSIFIER, user_query)
        parsed = _extract_json(raw)
        intent     = parsed.get('intent', 'clarify')
        confidence = float(parsed.get('confidence', 0.0))

        # Enforce confidence threshold
        if confidence < 0.70 or intent not in {
            'data_query', 'row_explanation', 'report_generation', 'clarify'
        }:
            intent = 'clarify'

        logger.info("intent=%s confidence=%.2f", intent, confidence)
        return {'intent': intent, 'error': None}

    except Exception as exc:
        logger.exception("intent_classifier failed: %s", exc)
        return {'intent': 'clarify', 'error': None}


# ── Node 2: Schema Retriever ──────────────────────────────────────────────────

def schema_retriever(state: dict) -> dict:
    """
    Identify which tables are relevant to the query and fetch their schemas.

    Asks the LLM to pick from QUERYABLE_TABLES, then fetches actual column
    metadata from information_schema (parameterised query — safe).
    Falls back to keyword matching if LLM fails.

    State reads:  messages, intent
    State writes: schema_context, relevant_tables, error
    """
    user_query = _get_user_query(state)

    # Step 1: Ask LLM to identify relevant tables
    table_list_str = '\n'.join(f'- {t}' for t in QUERYABLE_TABLES)
    selector_prompt = (
        f"{SYSTEM_PROMPT_SCHEMA_SELECTOR}\n\nAvailable tables:\n{table_list_str}"
    )

    try:
        raw = _call_llm(selector_prompt, user_query)
        # Parse JSON array
        try:
            tables = json.loads(raw)
            if not isinstance(tables, list):
                raise ValueError("Not a list")
            # Sanitise: only allow known tables
            tables = [t for t in tables if t in QUERYABLE_TABLES]
        except (json.JSONDecodeError, ValueError):
            tables = []

    except Exception:
        tables = []

    # Fallback to keyword matching
    if not tables:
        tables = identify_relevant_tables(user_query)

    # Step 2: Fetch schema from DB
    schema_str = build_schema_string(tables)

    logger.info("schema_retriever: tables=%s", tables)

    return {
        'schema_context':   schema_str,
        'relevant_tables':  tables,
        'error':            None,
    }


# ── Node 3: SQL Generator ─────────────────────────────────────────────────────

def sql_generator(state: dict) -> dict:
    """
    Generate a PostgreSQL SELECT query from the user's question.

    On retry (retry_count > 0): includes previous failed SQL and error message
    in the prompt so the LLM can learn from its mistake.

    State reads:  messages, schema_context, error, generated_sql, retry_count
    State writes: generated_sql, error
    """
    user_query    = _get_user_query(state)
    schema_ctx    = state.get('schema_context', '')
    retry_count   = state.get('retry_count', 0)
    prev_sql      = state.get('generated_sql', '')
    prev_error    = state.get('error', '')

    # Build context block
    fy_context = _get_india_fy_context()
    context_parts = [
        f"USER QUESTION:\n{user_query}",
        f"\nFINANCIAL YEAR CONTEXT:\n{fy_context}",
        f"\nRELEVANT DATABASE SCHEMA:\n{schema_ctx}",
    ]

    if retry_count > 0 and prev_sql:
        context_parts.append(
            f"\nPREVIOUS ATTEMPT (FAILED — DO NOT REPEAT THIS ERROR):\n"
            f"SQL:\n{prev_sql}\n\nError: {prev_error}\n\n"
            f"Please fix the specific problem and try again."
        )

    # Conversation history for multi-turn context
    history = state.get('conversation_history', [])
    if history:
        recent = history[-4:]  # last 2 turns
        history_str = "\n".join(
            f"{'User' if m.get('role') == 'user' else 'Assistant'}: {m.get('content', '')}"
            for m in recent
        )
        context_parts.append(f"\nCONVERSATION HISTORY:\n{history_str}")

    user_content = "\n".join(context_parts)

    try:
        sql = _call_llm(SYSTEM_PROMPT_SQL_GENERATOR, user_content)

        if not sql:
            return {
                'generated_sql': None,
                'error': "LLM did not return a SQL query.",
                'retry_count': retry_count + 1,
            }

        logger.info("sql_generator: generated SQL (retry=%d)", retry_count)
        return {'generated_sql': sql, 'error': None}

    except Exception as exc:
        logger.exception("sql_generator failed: %s", exc)
        return {
            'generated_sql': None,
            'error': f"Failed to generate SQL: {exc}",
            'retry_count': retry_count + 1,
        }


# ── Node 4: SQL Validator ─────────────────────────────────────────────────────

def sql_validator_node(state: dict) -> dict:
    """
    Validate and secure the LLM-generated SQL.

    Calls safety.validate_and_secure_sql() which:
    - Blocks non-SELECT statements
    - Injects parameterised tenant_id filter
    - Injects role-based filters (AUDITOR restrictions)
    - Enforces JOIN and table count limits

    State reads:  generated_sql, tenant_id, user_role, retry_count
    State writes: generated_sql (secured), sql_params, error, retry_count
    """
    raw_sql     = state.get('generated_sql', '')
    tenant_id   = state.get('tenant_id', '')
    user_role   = state.get('user_role', 'ANALYST')
    retry_count = state.get('retry_count', 0)

    if not raw_sql:
        return {
            'error':       'No SQL to validate.',
            'retry_count': retry_count + 1,
        }

    result = validate_and_secure_sql(raw_sql, tenant_id, user_role)

    if result.is_valid:
        return {
            'generated_sql': result.modified_sql,
            'sql_params':    result.params,
            'error':         None,
        }
    else:
        logger.warning("sql_validator: rejected | error=%s", result.error)
        return {
            'error':       result.error,
            'retry_count': retry_count + 1,
        }


# ── Node 5: SQL Executor ──────────────────────────────────────────────────────

def sql_executor(state: dict) -> dict:
    """
    Execute the validated, tenant-secured SQL query.

    Uses tools.execute_sql() which:
    - Sets statement_timeout = 10 seconds
    - Returns max MAX_ROWS_FOR_LLM (200) rows
    - Never logs raw SQL or result data

    State reads:  generated_sql, sql_params, retry_count
    State writes: query_result, no_results, execution_time_ms, error, retry_count
    """
    sql         = state.get('generated_sql', '')
    params      = state.get('sql_params', [])
    retry_count = state.get('retry_count', 0)

    if not sql:
        return {'error': 'No SQL available to execute.', 'retry_count': retry_count + 1}

    result = execute_sql(sql, params)

    if result.get('error'):
        logger.warning("sql_executor: DB error=%s", result['error'])
        return {
            'query_result':      [],
            'no_results':        True,
            'execution_time_ms': result.get('execution_time_ms', 0),
            'error':             result['error'],
            'retry_count':       retry_count + 1,
        }

    return {
        'query_result':      result['rows'],
        'no_results':        result['no_results'],
        'execution_time_ms': result.get('execution_time_ms', 0),
        'total_row_count':   result.get('total_row_count', 0),
        'truncated':         result.get('truncated', False),
        'error':             None,
    }


# ── Node 6: Response Formatter ────────────────────────────────────────────────

def response_formatter(state: dict) -> dict:
    """
    Format query results (or error/clarify state) into a human-readable answer.

    Handles all four intents:
    - data_query:        Formats result rows as prose + follow-up questions
    - row_explanation:   Fetches row + audit log, explains history and action
    - report_generation: Drafts BRSR narrative from available data
    - clarify:           Returns the suggested clarification question

    State reads:  intent, query_result, no_results, error, messages,
                  context_row_id, context_row_source, tenant_id
    State writes: answer, suggested_follow_ups
    """
    intent     = state.get('intent', 'clarify')
    user_query = _get_user_query(state)

    # ── Clarify path ──────────────────────────────────────────────────────────
    if intent == 'clarify':
        answer = (
            "I'd love to help, but I need a bit more detail. "
            "Could you tell me which scope (Scope 1, 2, or 3), "
            "time period, or facility you're asking about?"
        )
        return {
            'answer':             answer,
            'suggested_follow_ups': [
                "What are my total Scope 1+2 emissions this FY?",
                "Show me the Scope 2 trend for last 6 months",
                "Which rows are flagged as suspicious right now?",
            ],
        }

    # ── Row explanation path ──────────────────────────────────────────────────
    if intent == 'row_explanation':
        row_id     = state.get('context_row_id') or ''
        row_source = state.get('context_row_source') or 'SAP'
        tenant_id  = state.get('tenant_id') or ''

        row_data = get_row_with_audit(row_id, row_source, tenant_id)

        if row_data.get('error') or not row_data.get('row'):
            return {
                'answer': (
                    f"I couldn't find row {row_id} in your {row_source} data. "
                    "It may have been deleted or you may not have access to it."
                ),
                'suggested_follow_ups': [
                    "Which rows are flagged as suspicious?",
                    "Show me all recent audit actions",
                ],
            }

        row       = row_data['row']
        audit_log = row_data['audit_log']
        comments  = row_data['comments']

        context = (
            f"USER QUESTION:\n{user_query}\n\n"
            f"ROW DATA:\n{json.dumps(row, indent=2)}\n\n"
            f"AUDIT TRAIL ({len(audit_log)} entries):\n{json.dumps(audit_log, indent=2)}\n\n"
            f"COMMENTS/FINDINGS ({len(comments)} entries):\n{json.dumps(comments, indent=2)}"
        )

        raw = _call_llm(SYSTEM_PROMPT_RESPONSE_FORMATTER, context, use_formatter=True)
        return _parse_formatter_response(raw)

    # ── Report generation path ────────────────────────────────────────────────
    if intent == 'report_generation':
        # Use whatever query_result was fetched (if SQL ran) or note data unavailability
        result_rows = state.get('query_result', [])
        context = (
            f"USER REQUEST:\n{user_query}\n\n"
            f"AVAILABLE DATA ({len(result_rows)} rows):\n"
            f"{json.dumps(result_rows[:50], indent=2)}\n\n"
            "Please draft a 3-paragraph BRSR-ready narrative. "
            "If data is insufficient, state what additional information is needed."
        )
        raw = _call_llm(SYSTEM_PROMPT_RESPONSE_FORMATTER, context, use_formatter=True)
        return _parse_formatter_response(raw)

    # ── Data query path (main path) ───────────────────────────────────────────
    result_rows = state.get('query_result', [])
    no_results  = state.get('no_results', False)
    error       = state.get('error')
    truncated   = state.get('truncated', False)

    # If we exhausted retries with an error
    if error and not result_rows:
        return {
            'answer': (
                "I wasn't able to retrieve that data. "
                "This could be because the requested data doesn't exist yet, "
                "or the query was too complex. Try rephrasing your question."
            ),
            'suggested_follow_ups': [
                "What are my total Scope 2 emissions this FY?",
                "Show me Scope 1 emissions by plant",
                "Which rows are pending review?",
            ],
        }

    truncation_note = (
        f"\n\n[Note: Result was truncated to 200 rows — actual count may be higher]"
        if truncated else ''
    )

    context = (
        f"USER QUESTION:\n{user_query}\n\n"
        f"QUERY RESULTS ({len(result_rows)} rows):{truncation_note}\n"
        f"{json.dumps(result_rows[:50], indent=2)}\n\n"  # first 50 rows in prompt
        f"{'[No data found]' if no_results else ''}"
    )

    raw = _call_llm(SYSTEM_PROMPT_RESPONSE_FORMATTER, context, use_formatter=True)
    return _parse_formatter_response(raw)


def _parse_formatter_response(raw: str) -> dict:
    """
    Parse the LLM formatter response which contains the answer text
    and a trailing {"follow_ups": [...]} JSON block.
    """
    # Try to extract follow_ups JSON from the end of the response
    follow_ups = []
    answer = raw

    follow_up_match = re.search(
        r'\{"follow_ups"\s*:\s*\[.*?\]\}',
        raw, re.DOTALL
    )
    if follow_up_match:
        try:
            parsed = json.loads(follow_up_match.group())
            follow_ups = parsed.get('follow_ups', [])
            # Remove the JSON block from the answer text
            answer = raw[:follow_up_match.start()].strip()
        except json.JSONDecodeError:
            pass

    return {
        'answer':               answer or "I wasn't able to format a response for that data.",
        'suggested_follow_ups': follow_ups[:3],
    }


# ── Node 7: Output Classifier ─────────────────────────────────────────────────

def output_classifier(state: dict) -> dict:
    """
    Determine the optimal output type and configure chart settings if needed.

    Decision logic:
    - 0 results or clarify intent          → "text"
    - 1 value or short text answer         → "text"
    - 1-10 rows, 2-6 columns              → "table"
    - 11+ rows                             → "table" (paginated)
    - Columns contain a date + numeric     → "chart" (line)
    - Columns contain category + numeric   → "chart" (bar)
    - Single row with percentage columns   → "chart" (donut)

    State reads:  query_result, intent, response_type, answer
    State writes: response_type, chart_config
    """
    intent      = state.get('intent', 'clarify')
    rows        = state.get('query_result') or []
    answer      = state.get('answer', '')

    # Non-data intents always return text
    if intent in ('clarify', 'row_explanation', 'report_generation'):
        return {'response_type': 'text', 'chart_config': None}

    # No data returned → text response
    if not rows:
        return {'response_type': 'text', 'chart_config': None}

    # Single scalar value → text
    if len(rows) == 1 and len(rows[0]) == 1:
        return {'response_type': 'text', 'chart_config': None}

    col_names = list(rows[0].keys())
    n_rows    = len(rows)
    n_cols    = len(col_names)

    # ── Detect time-series ────────────────────────────────────────────────────
    date_cols = [c for c in col_names if any(
        kw in c.lower() for kw in ('month', 'date', 'period', 'week', 'year', 'quarter')
    )]
    numeric_cols = [c for c in col_names if any(
        kw in c.lower() for kw in ('co2', 'tonnes', 'kg', 'kwh', 'count', 'total', 'sum', 'amount', 'quantity')
    )]
    category_cols = [c for c in col_names if any(
        kw in c.lower() for kw in ('type', 'source', 'scope', 'plant', 'provider', 'status', 'material', 'fuel', 'description')
    )]
    pct_cols = [c for c in col_names if 'pct' in c.lower() or 'percent' in c.lower() or 'share' in c.lower()]

    # Time series → line chart
    if date_cols and numeric_cols and n_rows >= 3:
        x_key = date_cols[0]
        y_key = numeric_cols[0]
        y_label = 'tCO₂e' if 'tonne' in y_key.lower() or 'co2' in y_key.lower() else y_key
        return {
            'response_type': 'chart',
            'chart_config': {
                'type':      'line',
                'title':     _infer_chart_title(col_names),
                'x_key':     x_key,
                'y_key':     y_key,
                'color_key': category_cols[0] if category_cols else None,
                'y_label':   y_label,
                'x_label':   x_key.replace('_', ' ').title(),
            },
        }

    # Proportional breakdown → donut chart
    if pct_cols and n_rows <= 10:
        return {
            'response_type': 'chart',
            'chart_config': {
                'type':    'donut',
                'title':   _infer_chart_title(col_names),
                'x_key':   category_cols[0] if category_cols else col_names[0],
                'y_key':   pct_cols[0],
                'y_label': '%',
                'x_label': '',
            },
        }

    # Categorical + numeric → bar chart
    if category_cols and numeric_cols and n_rows <= 30:
        x_key = category_cols[0]
        y_key = numeric_cols[0]
        y_label = 'tCO₂e' if 'tonne' in y_key.lower() or 'co2' in y_key.lower() else y_key
        return {
            'response_type': 'chart',
            'chart_config': {
                'type':      'bar',
                'title':     _infer_chart_title(col_names),
                'x_key':     x_key,
                'y_key':     y_key,
                'color_key': None,
                'y_label':   y_label,
                'x_label':   x_key.replace('_', ' ').title(),
            },
        }

    # Default: table
    return {'response_type': 'table', 'chart_config': None}


def _infer_chart_title(col_names: list[str]) -> str:
    """Generate a human-readable chart title from column names."""
    if any('co2' in c.lower() or 'tonne' in c.lower() for c in col_names):
        if any('month' in c.lower() or 'date' in c.lower() for c in col_names):
            return 'Emissions Over Time'
        if any('type' in c.lower() or 'source' in c.lower() for c in col_names):
            return 'Emissions by Source'
        if any('plant' in c.lower() or 'facility' in c.lower() for c in col_names):
            return 'Emissions by Facility'
        return 'CO₂e Emissions'
    return 'Query Results'
