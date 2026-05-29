"""
apps/chatbot/views.py
=====================
Django REST endpoint for the LangGraph chatbot.

POST /api/v1/chatbot/query/

Responsibilities:
1. Validate request via ChatQuerySerializer
2. Enforce per-user rate limit (30 queries / hour via Django cache)
3. Extract tenant_id and user_role from the JWT via core.tenant helpers
4. Load conversation history from cache (Redis or LocMemCache)
5. Build initial AgentState and invoke the compiled LangGraph graph
6. Save updated conversation to cache (TTL 2h)
7. Return shaped ChatResponse

Security notes:
- Raw SQL is NEVER included in the response
- Raw DB results are NEVER logged
- tenant_id is extracted from the validated JWT, never from the request body
"""

import logging
import time
import uuid

from django.conf import settings
from django.core.cache import cache
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from langchain_core.messages import HumanMessage

from core.tenant import get_active_organisation, get_active_role
from .agent import run_agent
from .serializers import ChatQuerySerializer

logger = logging.getLogger(__name__)

# Cache key prefixes
_RATE_LIMIT_PREFIX = 'chatbot_rl'
_CONV_PREFIX       = 'chatbot_conv'

# Conversation TTL — clear after 2 hours of inactivity
_CONV_TTL_SECONDS = 7200

# Default rate limit (overridden by settings.CHATBOT_RATE_LIMIT)
_DEFAULT_RATE_LIMIT = 30


def _get_rate_limit() -> int:
    return getattr(settings, 'CHATBOT_RATE_LIMIT', _DEFAULT_RATE_LIMIT)


def _check_and_increment_rate_limit(user_id: str) -> tuple[bool, int]:
    """
    Check and increment the per-user hourly rate limit.

    Returns:
        (is_allowed: bool, seconds_until_reset: int)
    """
    current_hour = int(time.time() // 3600)
    cache_key = f"{_RATE_LIMIT_PREFIX}:{user_id}:{current_hour}"
    count = cache.get(cache_key, 0)
    limit = _get_rate_limit()

    if count >= limit:
        seconds_until_reset = 3600 - (int(time.time()) % 3600)
        return False, seconds_until_reset

    # Increment with 2-hour TTL so key eventually cleans itself up
    cache.set(cache_key, count + 1, timeout=_CONV_TTL_SECONDS)
    return True, 0


def _load_conversation(conversation_id: str) -> list:
    """Load conversation history from cache. Returns empty list if not found."""
    return cache.get(f"{_CONV_PREFIX}:{conversation_id}", [])


def _save_conversation(conversation_id: str, history: list) -> None:
    """
    Persist conversation history to cache.
    Keeps last 10 messages (5 turns) and resets TTL on every interaction.
    """
    cache.set(
        f"{_CONV_PREFIX}:{conversation_id}",
        history[-10:],          # keep last 5 user+assistant pairs
        timeout=_CONV_TTL_SECONDS,
    )


class ChatQueryView(APIView):
    """
    POST /api/v1/chatbot/query/

    Accepts a plain-English question and returns a structured answer
    (text, table, or chart) from the LangGraph Text-to-SQL agent.

    All three roles (ADMIN, ANALYST, AUDITOR) may use this endpoint.
    Role-based data restrictions are enforced inside the agent's sql_validator node.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        # ── 1. Validate request body ──────────────────────────────────────────
        serializer = ChatQuerySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated = serializer.validated_data
        user_message   = validated['message']
        conversation_id = str(validated.get('conversation_id') or uuid.uuid4())
        context_row_id  = str(validated['context_row_id']) if validated.get('context_row_id') else None
        context_row_source = validated.get('context_row_source')

        # ── 2. Rate limiting ──────────────────────────────────────────────────
        user_id = str(request.user.id)
        allowed, seconds_until_reset = _check_and_increment_rate_limit(user_id)
        if not allowed:
            minutes = max(1, seconds_until_reset // 60)
            return Response(
                {
                    "error": f"Rate limit reached. Try again in {minutes} minute(s).",
                    "retry_after_seconds": seconds_until_reset,
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        # ── 3. Resolve tenant context from JWT ────────────────────────────────
        org = get_active_organisation(request)
        if not org:
            return Response(
                {"error": "You are not associated with any organisation. Contact your admin."},
                status=status.HTTP_403_FORBIDDEN,
            )

        tenant_id = str(org.id)
        user_role = get_active_role(request) or 'ANALYST'

        # ── 4. Load conversation history ──────────────────────────────────────
        conversation_history = _load_conversation(conversation_id)

        # ── 5. Build initial agent state ──────────────────────────────────────
        initial_state = {
            'messages':             [HumanMessage(content=user_message)],
            'tenant_id':            tenant_id,
            'user_role':            user_role,
            'context_row_id':       context_row_id,
            'context_row_source':   context_row_source,
            'conversation_history': conversation_history,
        }

        # ── 6. Run the LangGraph agent ────────────────────────────────────────
        start_wall = int(time.time() * 1000)
        try:
            final_state = run_agent(initial_state)
        except Exception as exc:
            logger.exception(
                "Agent execution failed | user_id=%s tenant_id=%s",
                user_id, tenant_id,
            )
            return Response(
                {"error": "The assistant encountered an unexpected error. Please try again."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        wall_time_ms = int(time.time() * 1000) - start_wall

        # ── 7. Log query metadata (no SQL, no data) ───────────────────────────
        logger.info(
            "chatbot_query | user_id=%s tenant_id=%s role=%s intent=%s "
            "response_type=%s db_ms=%d wall_ms=%d rows=%d",
            user_id,
            tenant_id,
            user_role,
            final_state.get('intent'),
            final_state.get('response_type'),
            final_state.get('execution_time_ms', 0),
            wall_time_ms,
            final_state.get('total_row_count', 0),
        )

        # ── 8. Update conversation history ────────────────────────────────────
        new_history = conversation_history + [
            {'role': 'user',      'content': user_message},
            {'role': 'assistant', 'content': final_state.get('answer', '')},
        ]
        _save_conversation(conversation_id, new_history)

        # ── 9. Build response ─────────────────────────────────────────────────
        query_result  = final_state.get('query_result') or []
        response_type = final_state.get('response_type', 'text')

        # Separate table_data and chart_data based on response type
        table_data = None
        chart_data = None
        if response_type == 'table':
            table_data = query_result
        elif response_type == 'chart':
            chart_data = query_result

        return Response(
            {
                'conversation_id':      conversation_id,
                'message_id':           str(uuid.uuid4()),
                'intent':               final_state.get('intent'),
                'answer':               final_state.get('answer', ''),
                'response_type':        response_type,
                'table_data':           table_data,
                'chart_config':         final_state.get('chart_config'),
                'chart_data':           chart_data,
                'suggested_follow_ups': final_state.get('suggested_follow_ups', []),
                'execution_time_ms':    final_state.get('execution_time_ms', 0),
                'rows_returned':        len(query_result),
            },
            status=status.HTTP_200_OK,
        )
