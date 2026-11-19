-- Job Application Tracker: clean-install script (MySQL 8.0.16+ for CHECK constraints).
-- WARNING: this drops and recreates the four tables, so any existing data is lost.
-- It is safe to re-run on a fresh or existing job_tracker database.

CREATE DATABASE IF NOT EXISTS job_tracker;
USE job_tracker;

DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS contacts;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS companies;

CREATE TABLE companies (
    company_id INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(100) NOT NULL,
    industry VARCHAR(50),
    website VARCHAR(200),
    city VARCHAR(50),
    state VARCHAR(50),
    notes TEXT,
    CONSTRAINT uq_company_name UNIQUE (company_name)
);

-- A job may outlive its company (company_id becomes NULL if the company is deleted).
CREATE TABLE jobs (
    job_id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT,
    job_title VARCHAR(100) NOT NULL,
    job_type ENUM('Full-time','Part-time','Contract','Internship'),
    salary_min INT,
    salary_max INT,
    job_url VARCHAR(300),
    date_posted DATE,
    -- JSON object, e.g. {"required_skills": [...], "preferred_skills": [...], "remote_option": true}
    requirements JSON,
    CONSTRAINT fk_jobs_company FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT chk_salary_range CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max),
    CONSTRAINT chk_requirements_object CHECK (requirements IS NULL OR JSON_TYPE(requirements) = 'OBJECT')
);

-- An application cannot exist without its job: deleting a job deletes its applications.
CREATE TABLE applications (
    application_id INT PRIMARY KEY AUTO_INCREMENT,
    job_id INT NOT NULL,
    application_date DATE NOT NULL,
    status ENUM('Applied','Screening','Interview','Offer','Rejected','Withdrawn') NOT NULL DEFAULT 'Applied',
    resume_version VARCHAR(50),
    cover_letter_sent BOOLEAN NOT NULL DEFAULT FALSE,
    -- Free-form JSON, e.g. {"rounds": 2, "interviewer": "...", "notes": "..."}
    interview_data JSON,
    CONSTRAINT fk_applications_job FOREIGN KEY (job_id) REFERENCES jobs(job_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

-- A contact belongs to a company: deleting a company deletes its contacts.
CREATE TABLE contacts (
    contact_id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    contact_name VARCHAR(100) NOT NULL,
    title VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    linkedin_url VARCHAR(200),
    notes TEXT,
    CONSTRAINT fk_contacts_company FOREIGN KEY (company_id) REFERENCES companies(company_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);

INSERT INTO companies (company_name, industry, website, city, state, notes) VALUES
('TechCorp', 'Software', 'https://example.com/techcorp', 'Miami', 'Florida', 'Target company'),
('DataCo', 'Analytics', 'https://example.com/dataco', 'Austin', 'Texas', 'Strong data team');

INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max, job_url, date_posted, requirements) VALUES
(1, 'Software Developer', 'Full-time', 80000, 105000, 'https://example.com/jobs/1', CURDATE(),
 JSON_OBJECT('required_skills', JSON_ARRAY('Python','SQL','Flask'), 'preferred_skills', JSON_ARRAY('Docker','AWS'), 'remote_option', true)),
(2, 'Data Analyst', 'Full-time', 65000, 85000, 'https://example.com/jobs/2', CURDATE(),
 JSON_OBJECT('required_skills', JSON_ARRAY('SQL','Excel','Tableau'), 'preferred_skills', JSON_ARRAY('Python'), 'remote_option', false));
