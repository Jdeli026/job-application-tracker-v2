"""Route/SQL/HTML integration tests using an isolated database test double.

Run `python -m unittest discover -v`. These do not verify the MySQL server,
ENUM or native JSON types; perform the live checks in TESTING.md separately.
"""
import json
import unittest
from html.parser import HTMLParser
from mysql.connector import Error
from unittest.mock import patch
import app as web
from tests.support import TestDatabase


class FormParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.fields = []
        self.label_depth = 0
        self.unlabeled = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'label':
            self.label_depth += 1
        if tag in ('input', 'select', 'textarea') and attrs.get('name'):
            self.fields.append(attrs['name'])
            if not self.label_depth and not attrs.get('aria-label'):
                self.unlabeled.append(attrs['name'])

    def handle_endtag(self, tag):
        if tag == 'label':
            self.label_depth -= 1


class AppTests(unittest.TestCase):
    def setUp(self):
        self.db = TestDatabase()
        self.db.start()
        web.app.config.update(TESTING=True, SECRET_KEY='test-only')
        self.client = web.app.test_client()

    def tearDown(self):
        self.db.stop()

    def seed(self):
        self.client.post('/companies/add', data={'company_name': 'TechCorp'})
        self.client.post('/jobs/add', data={'company_id': '1', 'job_title': 'Developer',
                         'requirements': '{"required_skills":["Python","SQL","Flask"]}'})
        self.client.post('/applications/add', data={'job_id': '1', 'application_date': '2026-11-18'})
        self.client.post('/contacts/add', data={'company_id': '1', 'contact_name': 'Alex',
                                              'email': 'alex@example.com'})

    def test_all_pages_empty_and_populated(self):
        for populated in (False, True):
            if populated:
                self.seed()
            for path in ('/', '/companies', '/jobs', '/applications', '/contacts', '/job-match'):
                with self.subTest(path=path, populated=populated):
                    response = self.client.get(path)
                    self.assertEqual(response.status_code, 200)
                    parser = FormParser()
                    parser.feed(response.get_data(as_text=True))
                    self.assertEqual(parser.unlabeled, [])

    def test_full_crud_all_four_tables(self):
        self.seed()
        cases = [
            ('companies', 'company', {'company_name': 'Updated Corp'}, 'company_name', 'Updated Corp'),
            ('jobs', 'job', {'company_id': '1', 'job_title': 'Updated Role', 'salary_min': '0'}, 'job_title', 'Updated Role'),
            ('applications', 'application', {'job_id': '1', 'application_date': '2026-11-19',
              'status': 'Interview', 'cover_letter_sent': 'on', 'interview_data': '{"round":1}'}, 'status', 'Interview'),
            ('contacts', 'contact', {'company_id': '1', 'contact_name': 'Updated Alex'}, 'contact_name', 'Updated Alex')]
        for plural, kind, values, key, expected in cases:
            with self.subTest(table=plural):
                self.assertIsNotNone(self.db.one(f'SELECT * FROM {plural}'))
                page = self.client.get(f'/{plural}/1/edit')
                self.assertEqual(page.status_code, 200)
                parser = FormParser()
                parser.feed(page.get_data(as_text=True))
                self.assertFalse(parser.unlabeled)
                self.assertTrue(set(values).issubset(parser.fields))
                response = self.client.post(f'/{plural}/1/edit', data=values)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(self.db.one(f'SELECT * FROM {plural}')[key], expected)
                self.assertIn(expected, self.client.get(f'/{plural}').get_data(as_text=True))
        for plural in ('contacts', 'applications', 'jobs', 'companies'):
            self.assertEqual(self.client.post(f'/{plural}/1/delete').status_code, 302)
            self.assertEqual(self.db.all(f'SELECT * FROM {plural}'), [])

    def test_invalid_input_never_writes(self):
        self.seed()
        invalid = [('/companies/add', {'company_name': ' '}),
                   ('/companies/1/edit', {'company_name':'x', 'industry':'x'*51}),
                   ('/companies/1/edit', {'company_name':'x', 'website':'javascript:alert(1)'}),
                   ('/jobs/add', {'job_title':'x', 'salary_min':'100', 'salary_max':'10'}),
                   ('/jobs/add', {'job_title':'x', 'salary_min':'-1'}),
                   ('/jobs/add', {'job_title':'x', 'salary_min':'nope'}),
                   ('/jobs/add', {'job_title':'x', 'salary_max':'2147483648'}),
                   ('/jobs/add', {'job_title':'x', 'company_id':'999'}),
                   ('/jobs/add', {'job_title':'x', 'requirements':'{broken'}),
                   ('/jobs/add', {'job_title':'x', 'requirements':'{"required_skills":[],"extra":NaN}'}),
                   ('/jobs/add', {'job_title':'x', 'requirements':'[]'}),
                   ('/jobs/1/edit', {'job_title':'x', 'requirements':'{"required_skills":"SQL"}'}),
                   ('/jobs/add', {'job_title':'x', 'requirements':'{"required_skills":[null]}'}),
                   ('/applications/add', {'job_id':'999', 'application_date':'2026-11-18'}),
                   ('/applications/1/edit', {'job_id':'1', 'application_date':'2026-02-30'}),
                   ('/applications/add', {'job_id':'1', 'application_date':'2026-11-18','status':'Unknown'}),
                   ('/contacts/add', {'contact_name':'x','company_id':'1','email':'invalid'}),
                   ('/contacts/1/edit', {'contact_name':'x','company_id':'1','linkedin_url':'ftp://example.com'}),
                   ('/contacts/add', {'contact_name':'x','company_id':'1','phone':'1'*21}),
                   ('/contacts/add', {'contact_name':'x'}),
                   ('/contacts/1/edit', {'contact_name':'x','company_id':'999'})]
        with patch.object(web, 'execute') as execute:
            for path, data in invalid:
                with self.subTest(path=path, data=data):
                    response = self.client.post(path, data=data, follow_redirects=True)
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('flash danger', response.get_data(as_text=True))
            execute.assert_not_called()

    def test_match_percentages_and_unique_skills(self):
        self.seed()
        self.db.execute('INSERT INTO jobs(job_title,requirements) VALUES (%s,%s)',
                        ('Analyst',json.dumps({'required_skills':[' SQL ', 'sql', 'Excel']})))
        self.db.execute('INSERT INTO jobs(job_title,requirements) VALUES (%s,%s)', ('Empty','{}'))
        for skills, percentages in [(' python, SQL ', ['67','50','0']), ('Python, SQL, Flask, Excel',['100','100','0']), ('Rust',['0','0','0'])]:
            with self.subTest(skills=skills):
                response = self.client.post('/job-match', data={'skills':skills})
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                import re
                self.assertEqual(re.findall(r'<div class="score">(\d+)',html),percentages)
        blank = self.client.post('/job-match',data={'skills':' , '})
        self.assertIn('Enter at least one skill',blank.get_data(as_text=True))

    def test_missing_records_and_404(self):
        for table in ('companies','jobs','applications','contacts'):
            self.assertEqual(self.client.get(f'/{table}/999/edit').status_code,302)
            self.assertEqual(self.client.post(f'/{table}/999/delete').status_code,302)
        self.assertEqual(self.client.get('/unknown').status_code,404)

    def test_foreign_key_deletions_follow_new_schema(self):
        self.seed()
        self.client.post('/companies/1/delete')
        self.assertIsNone(self.db.one('SELECT * FROM jobs')['company_id'])
        self.assertEqual(self.db.all('SELECT * FROM contacts'), [])
        self.assertEqual(len(self.db.all('SELECT * FROM applications')), 1)
        self.client.post('/jobs/1/delete')
        self.assertEqual(self.db.all('SELECT * FROM applications'), [])
        self.assertEqual(self.client.get('/applications').status_code,200)

    def test_all_detail_views_and_relationship_links(self):
        self.seed()
        self.db.execute('UPDATE companies SET notes=%s', ('Company notes',))
        self.db.execute('UPDATE jobs SET salary_min=0, salary_max=95000')
        self.db.execute('UPDATE applications SET interview_data=%s', ('{"rounds":2}',))
        for plural, expected in [('companies', 'Company notes'), ('jobs', '$0'),
                                 ('applications', 'Cover letter sent'), ('contacts', 'alex@example.com')]:
            with self.subTest(table=plural):
                listing = self.client.get(f'/{plural}').get_data(as_text=True)
                self.assertIn(f'href="/{plural}/1"', listing)
                response = self.client.get(f'/{plural}/1')
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn(expected, html)
                self.assertIn(f'href="/{plural}/1/edit"', html)
                self.assertNotIn('<form', html)
                self.assertEqual(self.client.get(f'/{plural}/999').status_code, 404)
        company = self.client.get('/companies/1').get_data(as_text=True)
        self.assertIn('href="/jobs/1"', company)
        self.assertIn('href="/contacts/1"', company)
        job = self.client.get('/jobs/1').get_data(as_text=True)
        self.assertIn('href="/companies/1"', job)
        self.assertIn('href="/applications/1"', job)
        self.assertIn('required_skills', job)
        application = self.client.get('/applications/1').get_data(as_text=True)
        self.assertIn('rounds', application)
        self.assertIn('No', application)

    def test_details_escape_content_and_reject_unsafe_links(self):
        self.seed()
        self.db.execute('UPDATE companies SET notes=%s,website=%s',
                        ('<script>alert(1)</script>', 'javascript:alert(1)'))
        html = self.client.get('/companies/1').get_data(as_text=True)
        self.assertIn('&lt;script&gt;', html)
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertNotIn('href="javascript:', html)
        self.db.execute('UPDATE companies SET website=%s', ('https://example.com',))
        self.assertIn('href="https://example.com"', self.client.get('/companies/1').get_data(as_text=True))

    def test_unique_company_names_create_and_edit(self):
        self.seed()
        self.client.post('/companies/add', data={'company_name':'Other company'})
        for path in ('/companies/add', '/companies/2/edit'):
            response = self.client.post(path, data={'company_name':'techcorp'}, follow_redirects=True)
            self.assertIn('already exists', response.get_data(as_text=True))
            self.assertEqual(len(self.db.all('SELECT * FROM companies')), 2)
        response = self.client.post('/companies/1/edit', data={'company_name':'TechCorp'})
        self.assertEqual(response.status_code, 302)

    def test_contact_company_required_in_create_and_edit_forms(self):
        self.seed()
        for path in ('/contacts', '/contacts/1/edit'):
            html = self.client.get(path).get_data(as_text=True)
            self.assertIn('name="company_id" required', html)
        for path in ('/contacts/add', '/contacts/1/edit'):
            html = self.client.post(path, data={'contact_name':'Name'}, follow_redirects=True).get_data(as_text=True)
            self.assertIn('valid company is required', html)

    def test_delete_confirmations_describe_cascades(self):
        self.seed()
        self.assertIn('All linked contacts will also be deleted', self.client.get('/companies').get_data(as_text=True))
        self.assertIn('All linked applications will also be deleted', self.client.get('/jobs').get_data(as_text=True))

    def test_status_filter_options_and_escape_html(self):
        self.seed()
        self.db.execute('UPDATE companies SET company_name=%s', ('<script>alert(1)</script>',))
        html = self.client.get('/companies').get_data(as_text=True)
        self.assertNotIn('<script>alert(1)</script>',html)
        self.assertIn('&lt;script&gt;',html)
        html = self.client.get('/applications').get_data(as_text=True)
        for status in web.APP_STATUSES:
            self.assertIn(f'<option>{status}</option>',html)

    def test_database_failure_is_controlled(self):
        with patch.object(web,'fetch_one',side_effect=Error('Test connection failure')):
            response = self.client.get('/')
            self.assertEqual(response.status_code,500)
            self.assertIn('back on track',response.get_data(as_text=True))


if __name__ == '__main__':
    unittest.main()
