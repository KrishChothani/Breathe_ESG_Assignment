"""
apps/chatbot/tools.py
=====================
Database execution and schema introspection tools for the LangGraph agent.

Key functions:
  execute_sql()          — run a pre-validated parameterised query
  get_schema_for_tables() — fetch column metadata from information_schema
  get_row_with_audit()   — fetch a specific row + its audit trail for row_explanation

Security notes:
  - execute_sql() ONLY accepts pre-validated SQL (must call safety.validate_and_secure_sql first)
  - statement_timeout prevents runaway queries (10 seconds)
  - Results are capped at MAX_ROWS to prevent LLM token overflow
  - Logging records metadata only — never the raw SQL or result data
"""

import logging
import time
from decimal import Decimal
from datetime import date, datetime
from uuid import UUID

from django.db import connection, OperationalError, ProgrammingError

from .prompts import COLUMN_DESCRIPTIONS, QUERYABLE_TABLES

logger = logging.getLogger(__name__)

# Max rows the LLM will ever see — prevents token overflow
MAX_ROWS_FOR_LLM  = 200
# Max rows returned to the frontend (for large table views)
MAX_ROWS_FRONTEND = 500

# Columns to always exclude from schema introspection
_SCHEMA_EXCLUDED_COLUMNS = frozenset({
    'password', 'passwd', 'token', 'secret', 'api_key',
    'private_key', 'hash', 'salt',
})


# ── Type coercion helpers ─────────────────────────────────────────────────────

def _coerce_value(v):
    """
    Convert DB value types to JSON-serialisable Python primitives.
    Django's cursor returns psycopg2 types that need normalisation.
    """
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, memoryview):
        return None  # binary data — skip
    return v


def _rows_to_dicts(cursor) -> list[dict]:
    """Convert cursor fetchall results to list of dicts with coerced values."""
    cols = [desc[0] for desc in cursor.description]
    return [
        {col: _coerce_value(val) for col, val in zip(cols, row)}
        for row in cursor.fetchall()
    ]


# ── SQL Executor ──────────────────────────────────────────────────────────────

def execute_sql(
    sql: str,
    params: list,
    max_rows: int = MAX_ROWS_FOR_LLM,
) -> dict:
    """
    Execute a pre-validated parameterised SQL query.

    IMPORTANT: This function trusts that the SQL has already been validated
    by safety.validate_and_secure_sql(). Never call this directly with
    raw LLM output.

    Args:
        sql:      Validated, tenant-secured SQL string with %s placeholders.
        params:   Bind parameters (tenant_id values injected by safety layer).
        max_rows: Max rows to return (default MAX_ROWS_FOR_LLM = 200).

    Returns:
        {
            "rows":       list of dicts,
            "row_count":  int,
            "no_results": bool,
            "error":      str | None,
            "execution_time_ms": int,
        }
    """
    start_ms = int(time.time() * 1000)

    try:
        with connection.cursor() as cursor:
            # Set per-statement timeout (10 seconds) — Supabase supports this
            cursor.execute("SET LOCAL statement_timeout = 10000;")
            cursor.execute(sql, params)
            rows = _rows_to_dicts(cursor)

    except OperationalError as exc:
        elapsed = int(time.time() * 1000) - start_ms
        err_str = str(exc)
        logger.warning(
            "SQL execution OperationalError | elapsed_ms=%d error=%s",
            elapsed, err_str,
        )
        return {
            "rows": [], "row_count": 0, "no_results": True,
            "error": f"Database error: {err_str}",
            "execution_time_ms": elapsed,
        }

    except ProgrammingError as exc:
        elapsed = int(time.time() * 1000) - start_ms
        err_str = str(exc)
        logger.warning(
            "SQL execution ProgrammingError | elapsed_ms=%d error=%s",
            elapsed, err_str,
        )
        return {
            "rows": [], "row_count": 0, "no_results": True,
            "error": f"Query error: {err_str}",
            "execution_time_ms": elapsed,
        }

    except Exception as exc:
        elapsed = int(time.time() * 1000) - start_ms
        logger.exception("Unexpected SQL execution error | elapsed_ms=%d", elapsed)
        return {
            "rows": [], "row_count": 0, "no_results": True,
            "error": "An unexpected database error occurred.",
            "execution_time_ms": elapsed,
        }

    elapsed = int(time.time() * 1000) - start_ms
    total_rows = len(rows)
    truncated = total_rows > max_rows
    result_rows = rows[:max_rows]

    logger.info(
        "SQL executed | rows_total=%d rows_returned=%d truncated=%s elapsed_ms=%d",
        total_rows, len(result_rows), truncated, elapsed,
    )

    return {
        "rows":              result_rows,
        "row_count":         len(result_rows),
        "total_row_count":   total_rows,
        "no_results":        total_rows == 0,
        "truncated":         truncated,
        "error":             None,
        "execution_time_ms": elapsed,
    }


# ── Schema Retriever ──────────────────────────────────────────────────────────

def get_schema_for_tables(table_names: list[str]) -> dict[str, dict[str, str]]:
    """
    Fetch column name → data type mappings for the given tables from
    PostgreSQL's information_schema.columns.

    Filters out:
      - Tables not in QUERYABLE_TABLES (safety check)
      - Sensitive column names (password, token, etc.)

    Returns:
        {table_name: {column_name: data_type, ...}, ...}
    """
    # Sanitise: only allow tables from the whitelist
    safe_tables = [t for t in table_names if t in QUERYABLE_TABLES]
    if not safe_tables:
        return {}

    schema_data: dict[str, dict[str, str]] = {}

    try:
        with connection.cursor() as cursor:
            # Use parameterised query to avoid any injection
            placeholders = ', '.join(['%s'] * len(safe_tables))
            cursor.execute(
                f"""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name IN ({placeholders})
                ORDER BY table_name, ordinal_position
                """,
                safe_tables,
            )
            for table_name, column_name, data_type in cursor.fetchall():
                # Skip sensitive columns
                if column_name.lower() in _SCHEMA_EXCLUDED_COLUMNS:
                    continue
                schema_data.setdefault(table_name, {})[column_name] = data_type

    except Exception as exc:
        logger.exception("Schema fetch failed for tables=%s: %s", safe_tables, exc)

    return schema_data


def build_schema_string(table_names: list[str]) -> str:
    """
    Convenience function: fetch schema + format as compact string for LLM context.
    Format: "table_name: col(type)[description], ..."
    """
    schema_data = get_schema_for_tables(table_names)
    lines = []

    for table in table_names:
        if table not in schema_data:
            continue
        cols = []
        for col_name, col_type in schema_data[table].items():
            desc = COLUMN_DESCRIPTIONS.get(table, {}).get(col_name, '')
            desc_str = f"[{desc}]" if desc else ''
            # Shorten verbose type names
            short_type = col_type.replace('character varying', 'varchar').replace('timestamp with time zone', 'timestamptz')
            cols.append(f"{col_name}({short_type}){desc_str}")
        lines.append(f"\n{table}:\n  " + "\n  ".join(cols))

    return "\n".join(lines) if lines else "No schema available."


# ── Row + Audit Fetcher (for row_explanation intent) ─────────────────────────

def get_row_with_audit(
    row_id: str,
    source: str,
    tenant_id: str,
) -> dict:
    """
    Fetch a specific emission row plus its full audit trail.

    Used by the response_formatter node for the 'row_explanation' intent.
    All queries are parameterised with tenant_id for isolation.

    Args:
        row_id:    UUID of the emission row.
        source:    'SAP', 'UTILITY', or 'TRAVEL'.
        tenant_id: Active organisation UUID.

    Returns:
        {
            "row":       dict | None,
            "audit_log": list[dict],
            "comments":  list[dict],
            "error":     str | None,
        }
    """
    if not source:
        return {
            "row": None, "audit_log": [], "comments": [],
            "error": "Row source is required. Must be SAP, UTILITY, or TRAVEL.",
        }
    source_upper = source.upper()
    table_map = {
        'SAP':     'emissions_saprow',
        'UTILITY': 'emissions_utilityrow',
        'TRAVEL':  'emissions_travel_row',
    }
    table = table_map.get(source_upper)

    if not table:
        return {
            "row": None, "audit_log": [], "comments": [],
            "error": f"Unknown source type '{source}'. Must be SAP, UTILITY, or TRAVEL.",
        }

    result = {"row": None, "audit_log": [], "comments": [], "error": None}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET LOCAL statement_timeout = 5000;")

            # Fetch the row itself
            cursor.execute(
                f"SELECT * FROM {table} WHERE id = %s AND organisation_id = %s LIMIT 1",
                [row_id, tenant_id],
            )
            rows = _rows_to_dicts(cursor)
            result["row"] = rows[0] if rows else None

            if result["row"] is None:
                result["error"] = f"Row {row_id} not found in {source} data for your organisation."
                return result

            # Fetch audit log for this row
            cursor.execute(
                """
                SELECT action, performed_at, note, row_source
                FROM ingestion_auditlog
                WHERE row_id = %s AND organisation_id = %s
                ORDER BY performed_at ASC
                """,
                [row_id, tenant_id],
            )
            result["audit_log"] = _rows_to_dicts(cursor)

            # Fetch comments/findings
            cursor.execute(
                """
                SELECT body, is_finding, resolved, role_at_time, created_at
                FROM ingestion_rowcomment
                WHERE row_id = %s AND organisation_id = %s
                ORDER BY created_at ASC
                """,
                [row_id, tenant_id],
            )
            result["comments"] = _rows_to_dicts(cursor)

    except Exception as exc:
        logger.exception("get_row_with_audit failed | row_id=%s source=%s", row_id, source)
        result["error"] = "Failed to fetch row details. Please try again."

    return result


# ── Table identification helpers ──────────────────────────────────────────────

def identify_relevant_tables(user_message: str) -> list[str]:
    """
    Simple keyword-based table identification as a fallback when the LLM
    schema selector fails. Used to pre-populate schema_retriever's table list.
    """
    msg = user_message.lower()
    tables = []

    if any(w in msg for w in ['scope 1', 'sap', 'fuel', 'diesel', 'plant', 'combustion']):
        tables.append('emissions_saprow')
    if any(w in msg for w in ['scope 2', 'utility', 'electricity', 'kwh', 'meter', 'bill']):
        tables.append('emissions_utilityrow')
    if any(w in msg for w in ['scope 3', 'travel', 'flight', 'hotel', 'concur', 'navan']):
        tables.append('emissions_travel_row')
    if any(w in msg for w in ['audit', 'action', 'approved', 'rejected', 'history', 'trail']):
        tables.append('ingestion_auditlog')
    if any(w in msg for w in ['comment', 'finding', 'auditor', 'resolved']):
        tables.append('ingestion_rowcomment')
    if any(w in msg for w in ['factor', 'emission factor', 'ef', 'coefficient']):
        tables.append('ingestion_emissionfactor')
    if any(w in msg for w in ['airport', 'iata', 'route']):
        tables.append('lookup_airport')

    # If nothing matched, default to all three scope tables
    if not tables:
        tables = ['emissions_saprow', 'emissions_utilityrow', 'emissions_travel_row']

    return tables
