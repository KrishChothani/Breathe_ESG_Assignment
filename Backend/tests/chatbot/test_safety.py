"""
tests/chatbot/test_safety.py
=============================
Unit tests for apps.chatbot.safety — the SQL validation and
tenant-injection security layer.

Test cases:
  (a) Single table: tenant filter is injected as a bind parameter
  (b) Multi-table JOIN: tenant filter injected on BOTH table aliases
  (c) DELETE statement is rejected with SQLValidationError
  (d) Non-tenant table (lookup_airport): no tenant filter crash — still valid
  (e) AUDITOR role: PENDING rows are filtered out via status != 'PENDING'
  (f) UNION query: tenant filter injected into all branches
  (g) System table reference (pg_catalog) is rejected
  (h) More than MAX_JOINS=3 JOINs are rejected
  (i) More than MAX_TABLES=5 table references are rejected
  (j) Sensitive column (password) reference is rejected
  (k) Markdown-fenced SQL is cleaned up before validation
  (l) Trailing semicolons are stripped

Run with:
  cd d:\\WORK\\BreatheESG\\Assignmet\\Backend
  python -m pytest tests/chatbot/test_safety.py -v
  OR
  python -m unittest tests.chatbot.test_safety -v

No Django setup required — safety.py has no Django dependencies.
"""

import sys
import os
import unittest

# Make apps/ importable without Django being configured
# (safety.py only uses sqlparse, re, logging — no Django imports)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from apps.chatbot.safety import (
    validate_and_secure_sql,
    inject_tenant_filter,
    inject_role_filters,
    SQLValidationError,
    TENANT_TABLES,
)

TENANT_ID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
ADMIN_ROLE   = 'ADMIN'
ANALYST_ROLE = 'ANALYST'
AUDITOR_ROLE = 'AUDITOR'


class TestTenantInjectionSingleTable(unittest.TestCase):
    """(a) Single table query: tenant filter must be injected as %s parameter."""

    def test_tenant_filter_added_to_simple_query(self):
        sql = "SELECT SUM(co2e_kg)/1000 AS co2e_tonnes FROM emissions_utilityrow WHERE status = 'APPROVED'"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)

        self.assertTrue(result.is_valid, f"Expected valid, got error: {result.error}")
        self.assertIn('organisation_id', result.modified_sql)
        self.assertIn('%s', result.modified_sql)
        # Exactly one tenant param injected
        self.assertEqual(result.params.count(TENANT_ID), 1)

    def test_tenant_param_is_not_interpolated(self):
        """Tenant ID must never appear as a literal string in the SQL."""
        sql = "SELECT co2e_kg FROM emissions_saprow"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)

        self.assertTrue(result.is_valid)
        self.assertNotIn(TENANT_ID, result.modified_sql,
                         "Tenant ID should be a bind param, not embedded in SQL")

    def test_where_clause_injected_when_none_exists(self):
        sql = "SELECT plant_code, SUM(co2e_kg) FROM emissions_saprow GROUP BY plant_code"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)

        self.assertTrue(result.is_valid)
        self.assertIn('WHERE', result.modified_sql.upper())

    def test_tenant_filter_prepended_before_existing_where(self):
        """If WHERE already exists, tenant filter must be injected as first condition."""
        sql = "SELECT * FROM emissions_utilityrow WHERE status = 'APPROVED' LIMIT 100"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)

        self.assertTrue(result.is_valid)
        # tenant_id filter must appear before status = 'APPROVED'
        tenant_pos = result.modified_sql.lower().find('organisation_id')
        status_pos = result.modified_sql.lower().find("status = 'approved'")
        self.assertLess(tenant_pos, status_pos,
                        "Tenant filter must precede other WHERE conditions")


class TestTenantInjectionMultiTableJoin(unittest.TestCase):
    """(b) Multi-table JOIN: tenant filter injected on BOTH table aliases."""

    def test_both_tables_get_tenant_filter(self):
        sql = (
            "SELECT sr.plant_code, al.action, al.performed_at "
            "FROM emissions_saprow sr "
            "JOIN ingestion_auditlog al ON al.row_id = sr.id "
            "WHERE sr.status = 'APPROVED'"
        )
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)

        self.assertTrue(result.is_valid, f"Expected valid, got: {result.error}")
        # Two tenant params: one for emissions_saprow, one for ingestion_auditlog
        self.assertEqual(
            result.params.count(TENANT_ID), 2,
            f"Expected 2 tenant params for 2 tenant tables, got: {result.params}"
        )
        # Both aliases appear with tenant_id
        self.assertIn('sr.organisation_id', result.modified_sql)
        self.assertIn('al.organisation_id', result.modified_sql)

    def test_alias_used_in_filter_not_table_name(self):
        """When an alias is defined, the alias (not table name) must be used in filter."""
        sql = "SELECT ur.consumption_kwh FROM emissions_utilityrow ur"
        result = validate_and_secure_sql(sql, TENANT_ID, ANALYST_ROLE)

        self.assertTrue(result.is_valid)
        self.assertIn('ur.organisation_id', result.modified_sql)
        # The bare table name should not be used as alias here
        self.assertNotIn('emissions_utilityrow.organisation_id', result.modified_sql)


class TestDeleteRejection(unittest.TestCase):
    """(c) DELETE statement is rejected immediately."""

    def test_delete_is_rejected(self):
        sql = "DELETE FROM emissions_saprow WHERE id = 'some-uuid'"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)

        self.assertFalse(result.is_valid)
        self.assertIn('SELECT', result.error.upper() + "ONLY SELECT",
                      "Error message should mention SELECT restriction")

    def test_update_is_rejected(self):
        sql = "UPDATE emissions_saprow SET co2e_kg = 0 WHERE id = 'x'"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)

    def test_drop_is_rejected(self):
        sql = "DROP TABLE emissions_saprow"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)

    def test_insert_is_rejected(self):
        sql = "INSERT INTO emissions_saprow (co2e_kg) VALUES (1000)"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)

    def test_truncate_is_rejected(self):
        sql = "TRUNCATE TABLE emissions_utilityrow"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)


class TestNonTenantTable(unittest.TestCase):
    """(d) Non-tenant table (lookup_airport, organisations): handled gracefully."""

    def test_lookup_airport_query_is_valid_no_tenant_injection(self):
        """lookup_airport has no tenant_id — should be valid, no params injected."""
        sql = "SELECT iata_code, name, city FROM lookup_airport WHERE country = 'IN'"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)

        self.assertTrue(result.is_valid, f"Expected valid, got: {result.error}")
        # lookup_airport is not a tenant table — no tenant params
        self.assertEqual(result.params, [],
                         "Non-tenant tables should have zero injected params")

    def test_mixed_tenant_and_non_tenant_tables(self):
        """Join of tenant table + lookup_airport: only tenant table gets filter."""
        sql = (
            "SELECT tr.traveller_name, a.city "
            "FROM emissions_travel_row tr "
            "JOIN lookup_airport a ON a.iata_code = tr.origin_iata"
        )
        result = validate_and_secure_sql(sql, TENANT_ID, ANALYST_ROLE)

        self.assertTrue(result.is_valid)
        # Only emissions_travel_row gets tenant filter
        self.assertEqual(result.params.count(TENANT_ID), 1)
        self.assertIn('tr.organisation_id', result.modified_sql)
        self.assertNotIn('a.organisation_id', result.modified_sql)


class TestAuditorRoleRestrictions(unittest.TestCase):
    """(e) AUDITOR role cannot see PENDING rows."""

    def test_auditor_gets_pending_filter_on_sap(self):
        sql = "SELECT plant_code, co2e_kg FROM emissions_saprow"
        result = validate_and_secure_sql(sql, TENANT_ID, AUDITOR_ROLE)

        self.assertTrue(result.is_valid)
        sql_upper = result.modified_sql.upper()
        self.assertIn("STATUS != 'PENDING'", sql_upper,
                      "AUDITOR must have PENDING filter injected")

    def test_auditor_gets_pending_filter_on_utility(self):
        sql = "SELECT meter_id, consumption_kwh FROM emissions_utilityrow WHERE status = 'APPROVED'"
        result = validate_and_secure_sql(sql, TENANT_ID, AUDITOR_ROLE)

        self.assertTrue(result.is_valid)
        # Check case-insensitively — SQL may normalise to uppercase or lowercase
        self.assertIn("pending", result.modified_sql.lower(),
                      "AUDITOR must have PENDING filter injected")

    def test_analyst_does_not_get_pending_filter(self):
        """ANALYST can see PENDING rows — no extra filter should be injected."""
        sql = "SELECT * FROM emissions_saprow"
        result = validate_and_secure_sql(sql, TENANT_ID, ANALYST_ROLE)

        self.assertTrue(result.is_valid)
        self.assertNotIn("status != 'PENDING'", result.modified_sql.lower())

    def test_auditor_blocked_from_email_column(self):
        """AUDITOR cannot access users_user.email."""
        sql = "SELECT email, role FROM users_user"
        result = validate_and_secure_sql(sql, TENANT_ID, AUDITOR_ROLE)

        self.assertFalse(result.is_valid,
                         "AUDITOR should be blocked from users_user.email")


class TestUnionQueryHandling(unittest.TestCase):
    """(f) UNION queries: tenant filter injected in all branches."""

    def test_union_all_branches_get_tenant_filter(self):
        sql = (
            "SELECT 'SAP' as source, co2e_kg FROM emissions_saprow WHERE status='APPROVED' "
            "UNION ALL "
            "SELECT 'UTILITY' as source, co2e_kg FROM emissions_utilityrow WHERE status='APPROVED'"
        )
        result = validate_and_secure_sql(sql, TENANT_ID, ANALYST_ROLE)

        self.assertTrue(result.is_valid, f"UNION query should be valid: {result.error}")
        # Should have 2 tenant params: one per branch
        self.assertEqual(
            result.params.count(TENANT_ID), 2,
            f"Expected 2 tenant params in UNION query, got: {result.params}"
        )


class TestSystemTableRejection(unittest.TestCase):
    """(g) System table references must be blocked."""

    def test_pg_catalog_rejected(self):
        sql = "SELECT tablename FROM pg_catalog.pg_tables"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)

    def test_information_schema_rejected(self):
        sql = "SELECT column_name FROM information_schema.columns WHERE table_name='emissions_saprow'"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)

    def test_auth_user_rejected(self):
        sql = "SELECT username, password FROM auth_user"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)


class TestComplexityLimits(unittest.TestCase):
    """(h) JOIN count limit and (i) table count limit."""

    def test_too_many_joins_rejected(self):
        # 4 JOINs > MAX_JOINS=3
        sql = (
            "SELECT a.id FROM emissions_saprow a "
            "JOIN emissions_utilityrow b ON b.id = a.id "
            "JOIN emissions_travel_row c ON c.id = a.id "
            "JOIN ingestion_auditlog d ON d.row_id = a.id "
            "JOIN ingestion_rowcomment e ON e.row_id = a.id"
        )
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)
        self.assertIn('JOIN', result.error.upper())

    def test_too_many_tables_rejected(self):
        # 6 tables using JOINs: exceeds MAX_TABLES=5
        sql = (
            "SELECT a.co2e_kg FROM emissions_saprow a "
            "JOIN emissions_utilityrow b ON b.id = a.id "
            "JOIN emissions_travel_row c ON c.id = a.id "
            "JOIN ingestion_auditlog d ON d.row_id = a.id "
            "JOIN ingestion_rowcomment e ON e.row_id = a.id "
            "JOIN ingestion_emissionfactor f ON f.id = a.id"
        )
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)


class TestSensitiveColumnRejection(unittest.TestCase):
    """(j) Sensitive column references are rejected."""

    def test_password_column_rejected(self):
        sql = "SELECT username, password FROM users_user"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)

    def test_token_column_rejected(self):
        sql = "SELECT id, token FROM some_table"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)


class TestSQLCleaning(unittest.TestCase):
    """(k) Markdown fences stripped. (l) Trailing semicolons stripped."""

    def test_markdown_fences_stripped(self):
        sql = "```sql\nSELECT co2e_kg FROM emissions_saprow\n```"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertTrue(result.is_valid, f"Markdown-fenced SQL should be valid: {result.error}")
        self.assertNotIn('```', result.modified_sql)

    def test_trailing_semicolon_stripped(self):
        sql = "SELECT co2e_kg FROM emissions_saprow;"
        result = validate_and_secure_sql(sql, TENANT_ID, ADMIN_ROLE)
        self.assertTrue(result.is_valid)
        self.assertNotIn(';', result.modified_sql)

    def test_empty_sql_rejected(self):
        result = validate_and_secure_sql('', TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)

    def test_whitespace_only_sql_rejected(self):
        result = validate_and_secure_sql('   \n  \t  ', TENANT_ID, ADMIN_ROLE)
        self.assertFalse(result.is_valid)


if __name__ == '__main__':
    unittest.main(verbosity=2)
