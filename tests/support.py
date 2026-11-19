"""Isolated SQLite test double. Production always uses mysql.connector."""
import sqlite3
from unittest.mock import patch
import app as web


class TestDatabase:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript('''
            PRAGMA foreign_keys=ON;
            CREATE TABLE companies (company_id INTEGER PRIMARY KEY, company_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                industry TEXT, website TEXT, city TEXT, state TEXT, notes TEXT);
            CREATE TABLE jobs (job_id INTEGER PRIMARY KEY, company_id INTEGER REFERENCES companies
                ON DELETE SET NULL, job_title TEXT NOT NULL, job_type TEXT, salary_min INTEGER,
                salary_max INTEGER, job_url TEXT, date_posted TEXT, requirements TEXT,
                CHECK(salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max),
                CHECK(requirements IS NULL OR json_type(requirements)='object'));
            CREATE TABLE applications (application_id INTEGER PRIMARY KEY, job_id INTEGER NOT NULL REFERENCES jobs
                ON DELETE CASCADE, application_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Applied',
                resume_version TEXT, cover_letter_sent INTEGER NOT NULL DEFAULT 0, interview_data TEXT);
            CREATE TABLE contacts (contact_id INTEGER PRIMARY KEY, company_id INTEGER NOT NULL REFERENCES companies
                ON DELETE CASCADE, contact_name TEXT NOT NULL, title TEXT, email TEXT, phone TEXT,
                linkedin_url TEXT, notes TEXT);
        ''')

    def all(self, query, params=None):
        return [dict(row) for row in self.conn.execute(query.replace('%s', '?'), params or ())]

    def one(self, query, params=None):
        rows = self.all(query, params)
        return rows[0] if rows else None

    def execute(self, query, params=None):
        cursor = self.conn.execute(query.replace('%s', '?'), params or ())
        self.conn.commit()
        return cursor.lastrowid, cursor.rowcount

    def start(self):
        self.patches = [patch.object(web, 'fetch_all', self.all),
                        patch.object(web, 'fetch_one', self.one),
                        patch.object(web, 'execute', self.execute)]
        for item in self.patches:
            item.start()

    def stop(self):
        for item in reversed(self.patches):
            item.stop()
        self.conn.close()
