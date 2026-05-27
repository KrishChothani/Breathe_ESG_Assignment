"""
Tests for PlantLookup WERKS management system.
Run: python manage.py test apps.emissions.tests.test_plant_lookup
"""
import io
import csv
import uuid

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from apps.emissions.models import PlantLookup, SAPRow
from apps.users.models import User
from apps.ingestion.models import RawUpload


def make_user(role='ANALYST', username='analyst1'):
    u = User.objects.create_user(username=username, password='test1234', role=role)
    return u


def plant_payload(**kwargs):
    defaults = {
        'werks_code':    'TEST1',
        'plant_name':    'Test Plant One',
        'city':          'Mumbai',
        'country':       'IN',
        'region':        'ASIA_PACIFIC',
        'plant_type':    'MANUFACTURING',
        'default_scope': 'SCOPE_1',
    }
    defaults.update(kwargs)
    return defaults


class PlantLookupCRUDTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user()
        self.client.force_authenticate(user=self.user)
        self.list_url = '/api/v1/emissions/plant-lookup/'

    # ── Create ─────────────────────────────────────────────────────────────

    def test_create_plant_lookup_valid(self):
        res = self.client.post(self.list_url, plant_payload(), format='json')
        self.assertEqual(res.status_code, 201)
        self.assertEqual(PlantLookup.objects.count(), 1)
        plant = PlantLookup.objects.first()
        self.assertEqual(plant.werks_code, 'TEST1')
        self.assertEqual(plant.added_by, self.user)

    def test_create_duplicate_werks_code_fails(self):
        PlantLookup.objects.create(**plant_payload(), added_by=self.user)
        res = self.client.post(self.list_url, plant_payload(), format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('werks_code', res.data)

    def test_country_must_be_two_chars(self):
        payload = plant_payload(country='IND')  # 3 chars — invalid
        res = self.client.post(self.list_url, payload, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('country', res.data)

    # ── Deactivate ──────────────────────────────────────────────────────────

    def test_deactivate_sets_is_active_false(self):
        plant = PlantLookup.objects.create(**plant_payload(), added_by=self.user)
        url = f'/api/v1/emissions/plant-lookup/{plant.id}/deactivate/'
        res = self.client.post(url)
        self.assertEqual(res.status_code, 200)
        plant.refresh_from_db()
        self.assertFalse(plant.is_active)

    # ── Export CSV ──────────────────────────────────────────────────────────

    def test_export_csv_returns_all_plants(self):
        PlantLookup.objects.create(**plant_payload(), added_by=self.user)
        PlantLookup.objects.create(**plant_payload(werks_code='TEST2', plant_name='Test Plant Two'), added_by=self.user)
        res = self.client.get('/api/v1/emissions/plant-lookup/export/')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/csv')
        content = res.content.decode('utf-8')
        self.assertIn('TEST1', content)
        self.assertIn('TEST2', content)


class BulkCSVImportTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user(username='analyst2')
        self.client.force_authenticate(user=self.user)
        self.url = '/api/v1/emissions/plant-lookup/bulk-import/'

    def _make_csv(self, rows):
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=[
            'werks_code', 'plant_name', 'city', 'country', 'region',
            'plant_type', 'default_scope', 'state', 'postal_code',
        ])
        writer.writeheader()
        writer.writerows(rows)
        buf.seek(0)
        return io.BytesIO(buf.read().encode('utf-8'))

    def test_bulk_csv_import_creates_records(self):
        csv_file = self._make_csv([
            {'werks_code': 'CSV1', 'plant_name': 'CSV Plant One', 'city': 'Delhi',
             'country': 'IN', 'region': 'ASIA_PACIFIC', 'plant_type': 'OFFICE',
             'default_scope': 'SCOPE_2', 'state': 'Delhi', 'postal_code': ''},
            {'werks_code': 'CSV2', 'plant_name': 'CSV Plant Two', 'city': 'London',
             'country': 'GB', 'region': 'EUROPE', 'plant_type': 'OFFICE',
             'default_scope': 'SCOPE_2', 'state': '', 'postal_code': ''},
        ])
        res = self.client.post(self.url, {'file': csv_file}, format='multipart')
        self.assertEqual(res.status_code, 207)
        self.assertEqual(res.data['created'], 2)
        self.assertEqual(PlantLookup.objects.count(), 2)

    def test_bulk_csv_import_skips_duplicates_by_default(self):
        PlantLookup.objects.create(**plant_payload(werks_code='CSV1', plant_name='Existing'), added_by=self.user)
        csv_file = self._make_csv([
            {'werks_code': 'CSV1', 'plant_name': 'New Name', 'city': 'Mumbai',
             'country': 'IN', 'region': 'ASIA_PACIFIC', 'plant_type': 'MANUFACTURING',
             'default_scope': 'SCOPE_1', 'state': '', 'postal_code': ''},
        ])
        res = self.client.post(self.url, {'file': csv_file}, format='multipart')
        self.assertEqual(res.status_code, 207)
        self.assertEqual(res.data['skipped'], 1)
        self.assertEqual(res.data['created'], 0)
        # Original name should be unchanged
        self.assertEqual(PlantLookup.objects.get(werks_code='CSV1').plant_name, 'Existing')


class UnresolvedWERKSTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = make_user(username='analyst3')
        self.client.force_authenticate(user=self.user)

        # Create a RawUpload to satisfy FK
        self.upload = RawUpload.objects.create(
            source_type='SAP',
            original_filename='test.csv',
            uploaded_by=self.user,
        )

    def test_unresolved_werks_returns_only_missing_codes(self):
        # Known plant
        PlantLookup.objects.create(**plant_payload(werks_code='KNOWN'), added_by=self.user)
        # SAP row with known code — should NOT appear in unresolved
        SAPRow.objects.create(raw_upload=self.upload, plant_code='KNOWN', plant_name='Known Plant')
        # SAP row with unknown code — SHOULD appear
        SAPRow.objects.create(raw_upload=self.upload, plant_code='UNKNOWN_X', plant_name='')

        res = self.client.get('/api/v1/emissions/plant-lookup/unresolved/')
        self.assertEqual(res.status_code, 200)
        codes = [r['plant_code'] for r in res.data['unresolved']]
        self.assertNotIn('KNOWN', codes)
        self.assertIn('UNKNOWN_X', codes)
