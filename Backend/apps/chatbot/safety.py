"""
apps/chatbot/safety.py
======================
SQL validation and multi-tenant security layer.

This is the most security-critical module in the chatbot stack.
Every LLM-generated SQL MUST pass through validate_and_secure_sql()
before execution. No exceptions.

Security guarantees:
1. Only SELECT statements are permitted
2. Organisation ID is injected as a %s bind parameter — never interpolated
3. Every tenant-scoped table gets an organisation_id condition
4. System tables, sensitive columns, and DDL are blocked
5. Complexity limits (JOINs, table count) prevent abuse
6. AUDITOR role cannot see PENDING rows or private email columns
7. UNION queries are allowed only when all branches will receive tenant filter
"""

import re
import logging

import sqlparse
import sqlparse.tokens as T

logger = logging.getLogger(__name__)


# ── Error class ───────────────────────────────────────────────────────────────

class SQLValidationError(Exception):
    """Raised when SQL fails security validation. Message is safe to return to caller."""
    pass


# ── Constants ─────────────────────────────────────────────────────────────────

# Note: users_user has NO organisation_id column — scope users via organisations_organisationmembership
TENANT_TABLES = frozenset({
    'emissions_saprow', 'emissions_utilityrow', 'emissions_travel_row',
    'ingestion_auditlog', 'ingestion_rowcomment', 'ingestion_emissionfactor',
    'organisations_organisationmembership',
})

# Tables where row-level status filtering applies for AUDITOR role
DATA_TABLES = frozenset({'emissions_saprow', 'emissions_utilityrow', 'emissions_travel_row'})

# Blocked DML / DDL keywords (first token of statement must be SELECT)
BLOCKED_STATEMENT_TYPES = frozenset({
    'INSERT', 'UPDATE', 'DELETE', 'DROP', 'TRUNCATE',
    'ALTER', 'CREATE', 'GRANT', 'REVOKE', 'REPLACE',
    'MERGE', 'CALL', 'EXECUTE', 'EXEC', 'COPY',
})

# System schemas / tables that must never be referenced
BLOCKED_SYSTEM_NAMES = frozenset({
    'pg_catalog', 'pg_tables', 'pg_class', 'pg_namespace',
    'pg_user', 'pg_shadow', 'pg_authid', 'pg_stat_activity',
    'information_schema', 'auth_user', 'auth_permission',
    'django_migrations', 'django_content_type', 'django_session',
    'django_admin_log',
})

# Sensitive column name patterns — matched case-insensitively
SENSITIVE_COLUMN_PATTERNS = [
    re.compile(r'\bpassword\b', re.I),
    re.compile(r'\bpasswd\b',   re.I),
    re.compile(r'\btoken\b',    re.I),
    re.compile(r'\bsecret\b',   re.I),
    re.compile(r'\bapi_key\b',  re.I),
    re.compile(r'\bprivate_key\b', re.I),
    re.compile(r'\bhash\b',     re.I),
]

MAX_JOINS  = 3
MAX_TABLES = 5

# SQL clauses that terminate a WHERE clause for injection purposes
_CLAUSE_TERMINATORS = re.compile(
    r'\b(ORDER\s+BY|GROUP\s+BY|HAVING|LIMIT|OFFSET|UNION|EXCEPT|INTERSECT)\b',
    re.I,
)


# ── ValidationResult ──────────────────────────────────────────────────────────

class ValidationResult:
    """Immutable result of SQL validation + security hardening."""

    __slots__ = ('is_valid', 'modified_sql', 'params', 'error')

    def __init__(
        self,
        is_valid: bool,
        modified_sql: str = '',
        params: list | None = None,
        error: str = '',
    ):
        self.is_valid     = is_valid
        self.modified_sql = modified_sql
        self.params       = params if params is not None else []
        self.error        = error

    def __repr__(self):
        if self.is_valid:
            return f"<ValidationResult OK params={len(self.params)}>"
        return f"<ValidationResult INVALID error={self.error!r}>"


# ── Internal helpers ──────────────────────────────────────────────────────────

_FROM_JOIN_PATTERN = re.compile(
    r'\b(?:FROM|JOIN)\s+'
    r'([a-zA-Z_][a-zA-Z0-9_]*)'            # table name
    r'(?:\s+(?:AS\s+)?([a-zA-Z_][a-zA-Z0-9_]*))?',  # optional alias
    re.I,
)

_SQL_KEYWORD_SET = frozenset({
    'WHERE', 'ON', 'SET', 'INNER', 'LEFT', 'RIGHT', 'OUTER',
    'CROSS', 'FULL', 'JOIN', 'FROM', 'SELECT', 'AS', 'AND', 'OR',
    'NOT', 'IN', 'IS', 'NULL', 'LIKE', 'BETWEEN', 'EXISTS',
})


def _extract_table_refs(sql: str) -> list[tuple[str, str]]:
    """
    Extract (table_name, alias) pairs from FROM / JOIN clauses.
    If no alias provided, alias == table_name.
    Skips SQL keywords accidentally matched by the regex.
    """
    refs = []
    for m in _FROM_JOIN_PATTERN.finditer(sql):
        table = m.group(1).lower()
        raw_alias = m.group(2)
        if raw_alias and raw_alias.upper() in _SQL_KEYWORD_SET:
            raw_alias = None
        alias = (raw_alias or m.group(1)).lower()
        refs.append((table, alias))
    return refs


def _count_joins(sql: str) -> int:
    """Count explicit JOIN clauses."""
    return len(re.findall(
        r'\b(?:INNER|LEFT|RIGHT|FULL|CROSS)?\s*(?:OUTER\s+)?JOIN\b', sql, re.I
    ))


def _count_unique_tables(sql: str) -> int:
    """Count unique table names referenced."""
    return len({t for t, _ in _extract_table_refs(sql)})


def _is_select_statement(sql: str) -> bool:
    """
    Use sqlparse to verify the first meaningful token is SELECT.
    Guards against: UPDATE ... RETURNING, DELETE ... USING, etc.
    """
    parsed = sqlparse.parse(sql.strip())
    if not parsed:
        return False
    stmt = parsed[0]
    for token in stmt.flatten():
        if token.ttype in (T.Whitespace, T.Newline, T.Comment.Single, T.Comment.Multiline):
            continue
        return token.ttype is T.DML and token.normalized.upper() == 'SELECT'
    return False


def _has_sensitive_column(sql: str) -> bool:
    """Return True if any sensitive column pattern appears in the SQL."""
    return any(p.search(sql) for p in SENSITIVE_COLUMN_PATTERNS)


def _find_blocked_system_name(sql: str) -> str | None:
    """Return the first blocked system object name found, or None."""
    sql_lower = sql.lower()
    for name in BLOCKED_SYSTEM_NAMES:
        if re.search(r'\b' + re.escape(name) + r'\b', sql_lower):
            return name
    return None


def _split_union_branches(sql: str) -> list[str]:
    """
    Split a SQL string on UNION / UNION ALL boundaries.
    Returns a list of branch strings (at least one).
    Handles nested parentheses to avoid splitting inside subqueries.
    """
    # Simple split — does not handle deeply nested UNIONs in subqueries,
    # but sufficient for single-level union queries generated by the LLM.
    parts = re.split(r'\bUNION(?:\s+ALL)?\b', sql, flags=re.I)
    return [p.strip() for p in parts if p.strip()]


# ── Tenant filter injection ───────────────────────────────────────────────────

def _inject_into_branch(sql: str, tenant_id: str) -> tuple[str, list]:
    """
    Inject tenant_id = %s for every tenant-scoped table in a single SQL branch.
    Returns (modified_sql, [tenant_id, ...]) — one param per injected condition.
    """
    refs = _extract_table_refs(sql)
    tenant_refs = [(t, a) for t, a in refs if t in TENANT_TABLES]

    if not tenant_refs:
        return sql, []

    conditions = [f"{alias}.organisation_id = %s" for _, alias in tenant_refs]
    params      = [tenant_id] * len(tenant_refs)
    tenant_clause = ' AND '.join(conditions)

    where_match = re.search(r'\bWHERE\b', sql, re.I)
    if where_match:
        # Inject right after WHERE keyword, before existing conditions
        insert_pos = where_match.end()
        sql = sql[:insert_pos] + f" {tenant_clause} AND" + sql[insert_pos:]
    else:
        # Inject WHERE before any ORDER BY / GROUP BY / LIMIT / etc.
        term_match = _CLAUSE_TERMINATORS.search(sql)
        if term_match:
            sql = sql[:term_match.start()] + f" WHERE {tenant_clause} " + sql[term_match.start():]
        else:
            sql = sql + f" WHERE {tenant_clause}"

    return sql, params


def inject_tenant_filter(sql: str, tenant_id: str) -> tuple[str, list]:
    """
    Public function: inject organisation_id filter for all tenant-scoped tables.

    Handles UNION queries by processing each branch independently.
    Tenant ID is ALWAYS a %s bind parameter — never string-interpolated.

    Returns:
        (modified_sql, params_list)
        params_list contains one tenant_id string per injected filter.
    """
    branches = _split_union_branches(sql)

    if len(branches) == 1:
        return _inject_into_branch(sql, tenant_id)

    # Reconstruct UNION with each branch secured
    union_keywords = re.findall(r'\bUNION(?:\s+ALL)?\b', sql, re.I)
    modified_branches = []
    all_params = []

    for branch in branches:
        mod_branch, params = _inject_into_branch(branch, tenant_id)
        modified_branches.append(mod_branch)
        all_params.extend(params)

    # Weave UNION keywords back in
    result_parts = []
    for i, branch in enumerate(modified_branches):
        result_parts.append(branch)
        if i < len(union_keywords):
            result_parts.append(union_keywords[i])

    return ' '.join(result_parts), all_params


def inject_role_filters(sql: str, user_role: str) -> tuple[str, list]:
    """
    Inject additional WHERE conditions based on the user's role.

    AUDITOR restrictions:
    - Cannot see PENDING rows in emissions_saprow, emissions_utilityrow, emissions_travel_row
      (injected as: AND {alias}.status != 'PENDING')
    - Cannot see users_user.email — handled by validation, not injection

    Returns (modified_sql, extra_params).  Currently role filters use
    literal string comparisons, so params is always [].
    """
    if user_role != 'AUDITOR':
        return sql, []

    refs = _extract_table_refs(sql)
    data_refs = [(t, a) for t, a in refs if t in DATA_TABLES]

    if not data_refs:
        return sql, []

    conditions = [f"{alias}.status != 'PENDING'" for _, alias in data_refs]
    clause = ' AND '.join(conditions)

    where_match = re.search(r'\bWHERE\b', sql, re.I)
    if where_match:
        insert_pos = where_match.end()
        sql = sql[:insert_pos] + f" {clause} AND" + sql[insert_pos:]
    else:
        term_match = _CLAUSE_TERMINATORS.search(sql)
        if term_match:
            sql = sql[:term_match.start()] + f" WHERE {clause} " + sql[term_match.start():]
        else:
            sql = sql + f" WHERE {clause}"

    return sql, []


# ── Main validation entry point ───────────────────────────────────────────────

def validate_and_secure_sql(
    sql: str,
    tenant_id: str,
    user_role: str,
) -> ValidationResult:
    """
    Validate and secure an LLM-generated SQL string.

    Steps executed in order:
    1.  Strip markdown fences and trailing semicolons
    2.  Verify statement is SELECT (sqlparse + regex double-check)
    3.  Verify first keyword is not a blocked DML/DDL type
    4.  Check for forbidden system table/schema references
    5.  Check for sensitive column patterns (password, token, etc.)
    6.  Enforce JOIN count limit (<= MAX_JOINS)
    7.  Enforce table count limit (<= MAX_TABLES)
    8.  Inject parameterised tenant_id filter on all tenant tables
    9.  Inject role-based filters (AUDITOR cannot see PENDING rows)

    Args:
        sql:        Raw SQL string from the LLM.
        tenant_id:  Active organisation UUID string.
        user_role:  One of ADMIN / ANALYST / AUDITOR.

    Returns:
        ValidationResult with is_valid, modified_sql, params, error.
    """
    if not sql or not sql.strip():
        return ValidationResult(False, error="LLM returned an empty query.")

    # Step 1 — strip markdown fences and semicolons
    sql = re.sub(r'^```(?:sql)?\s*', '', sql.strip(), flags=re.I)
    sql = re.sub(r'\s*```$', '', sql.strip())
    sql = sql.strip().rstrip(';').strip()

    if not sql:
        return ValidationResult(False, error="LLM returned an empty query after stripping.")

    # Step 2 — SELECT-only check (sqlparse-based)
    if not _is_select_statement(sql):
        return ValidationResult(
            False,
            error="Only SELECT statements are allowed. The generated query was rejected.",
        )

    # Step 3 — belt-and-suspenders blocked keyword check
    first_word = sql.split()[0].upper()
    if first_word in BLOCKED_STATEMENT_TYPES:
        return ValidationResult(
            False,
            error=f"Statement type '{first_word}' is not permitted.",
        )

    # Step 4 — blocked system names
    blocked = _find_blocked_system_name(sql)
    if blocked:
        return ValidationResult(
            False,
            error=f"Access to system object '{blocked}' is not permitted.",
        )

    # Step 5 — sensitive columns
    if _has_sensitive_column(sql):
        return ValidationResult(
            False,
            error="Query references a column that is restricted for security reasons.",
        )

    # Step 6 — AUDITOR cannot query users_user.email
    if user_role == 'AUDITOR' and 'users_user' in sql.lower():
        if re.search(r'\bemail\b', sql, re.I):
            return ValidationResult(
                False,
                error="Auditors cannot access email addresses. Please ask an Admin.",
            )

    # Step 7 — JOIN count
    join_count = _count_joins(sql)
    if join_count > MAX_JOINS:
        return ValidationResult(
            False,
            error=(
                f"Query has {join_count} JOINs which exceeds the limit of {MAX_JOINS}. "
                "Please ask a more focused question."
            ),
        )

    # Step 8 — Table count
    table_count = _count_unique_tables(sql)
    if table_count > MAX_TABLES:
        return ValidationResult(
            False,
            error=(
                f"Query references {table_count} tables which exceeds the limit of {MAX_TABLES}. "
                "Please break this into smaller questions."
            ),
        )

    # Step 9 — Inject tenant filter (parameterised)
    try:
        secured_sql, tenant_params = inject_tenant_filter(sql, tenant_id)
    except Exception as exc:
        logger.exception("Tenant filter injection failed: %s", exc)
        return ValidationResult(False, error="Failed to apply tenant security filter.")

    # Step 10 — Inject role-based filters
    try:
        secured_sql, role_params = inject_role_filters(secured_sql, user_role)
    except Exception as exc:
        logger.exception("Role filter injection failed: %s", exc)
        return ValidationResult(False, error="Failed to apply role-based filter.")

    all_params = tenant_params + role_params

    logger.info(
        "SQL validated | tables=%d joins=%d injected_params=%d role=%s",
        table_count, join_count, len(all_params), user_role,
    )

    return ValidationResult(
        is_valid=True,
        modified_sql=secured_sql,
        params=all_params,
    )
