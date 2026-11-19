import json
import re
import os
import secrets
from urllib.parse import urlsplit
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from mysql.connector import Error
from database import fetch_all, fetch_one, execute

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY") or secrets.token_hex(32)

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]
APP_STATUSES = ["Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

def opt(value):
    value = (value or "").strip()
    return value if value else None

def int_or_none(value):
    value = opt(value)
    if value is None:
        return None
    return int(value)

def json_or_none(value):
    value = opt(value)
    if value is None:
        return None
    # MySQL JSON rejects non-standard NaN/Infinity values accepted by Python.
    def reject_constant(constant):
        raise ValueError(f"Invalid JSON constant: {constant}")
    return json.dumps(json.loads(value, parse_constant=reject_constant), allow_nan=False)

def valid_date(value):
    if not value:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def positive_or_none(value):
    number = int_or_none(value)
    if number is not None and number < 0:
        raise ValueError("Number cannot be negative.")
    if number is not None and number > 2147483647:
        raise ValueError("Number exceeds the MySQL INT range.")
    return number

def company_exists(company_id):
    if company_id is None:
        return True
    return fetch_one("SELECT company_id FROM companies WHERE company_id=%s", (company_id,)) is not None

def job_exists(job_id):
    if job_id is None:
        return False
    return fetch_one("SELECT job_id FROM jobs WHERE job_id=%s", (job_id,)) is not None


@app.before_request
def validate_text_fields():
    """Apply the schema's length limits to both create and update forms."""
    if request.method != "POST":
        return None
    limits = {
        "company_name": 100, "industry": 50, "website": 200,
        "city": 50, "state": 50, "job_title": 100, "job_url": 300,
        "resume_version": 50, "contact_name": 100, "title": 100,
        "email": 100, "phone": 20, "linkedin_url": 200, "skills": 3000,
    }
    error = None
    for name, limit in limits.items():
        value = (request.form.get(name) or "").strip()
        if len(value) > limit:
            error = f"{name.replace('_', ' ').capitalize()} must be {limit} characters or fewer."
            break
    if not error:
        for name in ("website", "job_url", "linkedin_url"):
            value = opt(request.form.get(name))
            if value:
                try:
                    parsed = urlsplit(value)
                    valid = parsed.scheme in ("http", "https") and bool(parsed.hostname)
                except ValueError:
                    valid = False
                if not valid:
                    error = f"{name.replace('_', ' ').capitalize()} must be a valid http:// or https:// URL."
                    break
    if error:
        flash(error, "danger")
        # Use a known local GET route, never the untrusted Referer header.
        if request.endpoint and request.endpoint.startswith("edit_"):
            return redirect(url_for(request.endpoint, **request.view_args))
        destination = {"add_company": "companies", "add_job": "jobs",
                       "add_application": "applications", "add_contact": "contacts"}
        return redirect(url_for(destination.get(request.endpoint, "job_match")))

@app.context_processor
def inject_globals():
    return {"JOB_TYPES": JOB_TYPES, "APP_STATUSES": APP_STATUSES}

@app.route("/")
def dashboard():
    stats = {}
    for table in ("companies", "jobs", "applications", "contacts"):
        stats[table] = fetch_one(f"SELECT COUNT(*) AS count FROM {table}")["count"]

    status_counts = fetch_all("""
        SELECT status, COUNT(*) AS count
        FROM applications
        GROUP BY status
        ORDER BY count DESC, status
    """)

    recent_apps = fetch_all("""
        SELECT a.application_id, a.application_date, a.status,
               j.job_title, c.company_name
        FROM applications a
        LEFT JOIN jobs j ON a.job_id=j.job_id
        LEFT JOIN companies c ON j.company_id=c.company_id
        ORDER BY a.application_date DESC, a.application_id DESC
        LIMIT 8
    """)

    return render_template(
        "dashboard.html",
        stats=stats,
        status_counts=status_counts,
        recent_apps=recent_apps
    )

# -------------------- Companies --------------------

@app.route("/companies")
def companies():
    rows = fetch_all("SELECT * FROM companies ORDER BY company_name")
    return render_template("companies.html", companies=rows)


def company_name_taken(name, current_id=0):
    return fetch_one(
        "SELECT company_id FROM companies WHERE company_name=%s AND company_id<>%s",
        (name, current_id),
    ) is not None

@app.post("/companies/add")
def add_company():
    name = (request.form.get("company_name") or "").strip()
    if not name:
        flash("Company name is required.", "danger")
        return redirect(url_for("companies"))
    if len(name) > 100:
        flash("Company name must be 100 characters or fewer.", "danger")
        return redirect(url_for("companies"))

    if company_name_taken(name):
        flash("A company with that name already exists.", "danger")
        return redirect(url_for("companies"))

    website = opt(request.form.get("website"))
    if website and len(website) > 200:
        flash("Website must be 200 characters or fewer.", "danger")
        return redirect(url_for("companies"))

    execute("""
        INSERT INTO companies
        (company_name, industry, website, city, state, notes)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, (
        name,
        opt(request.form.get("industry")),
        website,
        opt(request.form.get("city")),
        opt(request.form.get("state")),
        opt(request.form.get("notes"))
    ))
    flash("Company added.", "success")
    return redirect(url_for("companies"))

@app.route("/companies/<int:item_id>/edit", methods=["GET", "POST"])
def edit_company(item_id):
    company = fetch_one("SELECT * FROM companies WHERE company_id=%s", (item_id,))
    if not company:
        flash("Company not found.", "danger")
        return redirect(url_for("companies"))

    if request.method == "POST":
        name = (request.form.get("company_name") or "").strip()
        if not name:
            flash("Company name is required.", "danger")
            return redirect(url_for("edit_company", item_id=item_id))
        if len(name) > 100:
            flash("Company name must be 100 characters or fewer.", "danger")
            return redirect(url_for("edit_company", item_id=item_id))

        if company_name_taken(name, item_id):
            flash("A company with that name already exists.", "danger")
            return redirect(url_for("edit_company", item_id=item_id))

        execute("""
            UPDATE companies
            SET company_name=%s, industry=%s, website=%s, city=%s, state=%s, notes=%s
            WHERE company_id=%s
        """, (
            name,
            opt(request.form.get("industry")),
            opt(request.form.get("website")),
            opt(request.form.get("city")),
            opt(request.form.get("state")),
            opt(request.form.get("notes")),
            item_id
        ))
        flash("Company updated.", "success")
        return redirect(url_for("companies"))

    return render_template("company_edit.html", company=company)

@app.post("/companies/<int:item_id>/delete")
def delete_company(item_id):
    if not fetch_one("SELECT company_id FROM companies WHERE company_id=%s", (item_id,)):
        flash("Company not found.", "danger")
        return redirect(url_for("companies"))
    execute("DELETE FROM companies WHERE company_id=%s", (item_id,))
    flash("Company deleted. Linked contacts were deleted; linked jobs were kept without a company.", "success")
    return redirect(url_for("companies"))

# -------------------- Jobs --------------------

@app.route("/jobs")
def jobs():
    rows = fetch_all("""
        SELECT j.*, c.company_name
        FROM jobs j
        LEFT JOIN companies c ON j.company_id=c.company_id
        ORDER BY j.date_posted DESC, j.job_id DESC
    """)
    companies_list = fetch_all(
        "SELECT company_id, company_name FROM companies ORDER BY company_name"
    )
    return render_template("jobs.html", jobs=rows, companies=companies_list)

def validate_job_form():
    title = (request.form.get("job_title") or "").strip()
    if not title:
        return None, "Job title is required."
    if len(title) > 100:
        return None, "Job title must be 100 characters or fewer."

    job_type = opt(request.form.get("job_type"))
    if job_type and job_type not in JOB_TYPES:
        return None, "Invalid job type."

    try:
        company_id = int_or_none(request.form.get("company_id"))
        salary_min = positive_or_none(request.form.get("salary_min"))
        salary_max = positive_or_none(request.form.get("salary_max"))
    except ValueError:
        return None, "Company and salary fields must contain valid numbers; salaries must be between 0 and 2,147,483,647."

    if company_id is not None and not company_exists(company_id):
        return None, "Selected company does not exist."

    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        return None, "Minimum salary cannot be greater than maximum salary."

    date_posted = opt(request.form.get("date_posted"))
    if date_posted and not valid_date(date_posted):
        return None, "Date posted must be a valid date."

    try:
        requirements = json_or_none(request.form.get("requirements"))
    except ValueError:
        return None, "Requirements must be valid JSON."

    if requirements:
        parsed = json.loads(requirements)
        if not isinstance(parsed, dict):
            return None, "Requirements must be a JSON object."
        for key in ("required_skills", "preferred_skills"):
            if key in parsed and (not isinstance(parsed[key], list) or
                    any(not isinstance(skill, str) or not skill.strip() for skill in parsed[key])):
                return None, f"{key} must be an array of non-empty skill names."

    data = (
        company_id,
        title,
        job_type,
        salary_min,
        salary_max,
        opt(request.form.get("job_url")),
        date_posted,
        requirements
    )
    return data, None

@app.post("/jobs/add")
def add_job():
    data, error = validate_job_form()
    if error:
        flash(error, "danger")
        return redirect(url_for("jobs"))

    execute("""
        INSERT INTO jobs
        (company_id, job_title, job_type, salary_min, salary_max,
         job_url, date_posted, requirements)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, data)

    flash("Job added.", "success")
    return redirect(url_for("jobs"))

@app.route("/jobs/<int:item_id>/edit", methods=["GET", "POST"])
def edit_job(item_id):
    job = fetch_one("SELECT * FROM jobs WHERE job_id=%s", (item_id,))
    companies_list = fetch_all(
        "SELECT company_id, company_name FROM companies ORDER BY company_name"
    )

    if not job:
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))

    if request.method == "POST":
        data, error = validate_job_form()
        if error:
            flash(error, "danger")
            return redirect(url_for("edit_job", item_id=item_id))

        execute("""
            UPDATE jobs
            SET company_id=%s, job_title=%s, job_type=%s, salary_min=%s,
                salary_max=%s, job_url=%s, date_posted=%s, requirements=%s
            WHERE job_id=%s
        """, data + (item_id,))
        flash("Job updated.", "success")
        return redirect(url_for("jobs"))

    return render_template("job_edit.html", job=job, companies=companies_list)

@app.post("/jobs/<int:item_id>/delete")
def delete_job(item_id):
    if not fetch_one("SELECT job_id FROM jobs WHERE job_id=%s", (item_id,)):
        flash("Job not found.", "danger")
        return redirect(url_for("jobs"))
    execute("DELETE FROM jobs WHERE job_id=%s", (item_id,))
    flash("Job deleted. Any linked applications were also deleted.", "success")
    return redirect(url_for("jobs"))

# -------------------- Applications --------------------

@app.route("/applications")
def applications():
    rows = fetch_all("""
        SELECT a.*, j.job_title, c.company_name
        FROM applications a
        LEFT JOIN jobs j ON a.job_id=j.job_id
        LEFT JOIN companies c ON j.company_id=c.company_id
        ORDER BY a.application_date DESC, a.application_id DESC
    """)
    jobs_list = fetch_all("""
        SELECT j.job_id, j.job_title, c.company_name
        FROM jobs j
        LEFT JOIN companies c ON j.company_id=c.company_id
        ORDER BY c.company_name, j.job_title
    """)
    return render_template("applications.html", applications=rows, jobs=jobs_list)

def validate_application_form():
    try:
        job_id = int_or_none(request.form.get("job_id"))
    except ValueError:
        return None, "Please select a valid job."

    if not job_exists(job_id):
        return None, "A valid job is required."

    application_date = opt(request.form.get("application_date"))
    if not valid_date(application_date):
        return None, "A valid application date is required."

    status = request.form.get("status") or "Applied"
    if status not in APP_STATUSES:
        return None, "Invalid application status."

    try:
        interview_data = json_or_none(request.form.get("interview_data"))
    except ValueError:
        return None, "Interview data must be valid JSON."

    resume_version = opt(request.form.get("resume_version"))
    if resume_version and len(resume_version) > 50:
        return None, "Resume version must be 50 characters or fewer."

    data = (
        job_id,
        application_date,
        status,
        resume_version,
        1 if request.form.get("cover_letter_sent") == "on" else 0,
        interview_data
    )
    return data, None

@app.post("/applications/add")
def add_application():
    data, error = validate_application_form()
    if error:
        flash(error, "danger")
        return redirect(url_for("applications"))

    execute("""
        INSERT INTO applications
        (job_id, application_date, status, resume_version,
         cover_letter_sent, interview_data)
        VALUES (%s,%s,%s,%s,%s,%s)
    """, data)
    flash("Application added.", "success")
    return redirect(url_for("applications"))

@app.route("/applications/<int:item_id>/edit", methods=["GET", "POST"])
def edit_application(item_id):
    application = fetch_one(
        "SELECT * FROM applications WHERE application_id=%s", (item_id,)
    )
    jobs_list = fetch_all("""
        SELECT j.job_id, j.job_title, c.company_name
        FROM jobs j
        LEFT JOIN companies c ON j.company_id=c.company_id
        ORDER BY c.company_name, j.job_title
    """)

    if not application:
        flash("Application not found.", "danger")
        return redirect(url_for("applications"))

    if request.method == "POST":
        data, error = validate_application_form()
        if error:
            flash(error, "danger")
            return redirect(url_for("edit_application", item_id=item_id))

        execute("""
            UPDATE applications
            SET job_id=%s, application_date=%s, status=%s, resume_version=%s,
                cover_letter_sent=%s, interview_data=%s
            WHERE application_id=%s
        """, data + (item_id,))
        flash("Application updated.", "success")
        return redirect(url_for("applications"))

    return render_template(
        "application_edit.html",
        application=application,
        jobs=jobs_list
    )

@app.post("/applications/<int:item_id>/delete")
def delete_application(item_id):
    if not fetch_one(
        "SELECT application_id FROM applications WHERE application_id=%s", (item_id,)
    ):
        flash("Application not found.", "danger")
        return redirect(url_for("applications"))

    execute("DELETE FROM applications WHERE application_id=%s", (item_id,))
    flash("Application deleted.", "success")
    return redirect(url_for("applications"))

# -------------------- Contacts --------------------

@app.route("/contacts")
def contacts():
    rows = fetch_all("""
        SELECT ct.*, c.company_name
        FROM contacts ct
        LEFT JOIN companies c ON ct.company_id=c.company_id
        ORDER BY ct.contact_name
    """)
    companies_list = fetch_all(
        "SELECT company_id, company_name FROM companies ORDER BY company_name"
    )
    return render_template("contacts.html", contacts=rows, companies=companies_list)

def validate_contact_form():
    name = (request.form.get("contact_name") or "").strip()
    if not name:
        return None, "Contact name is required."
    if len(name) > 100:
        return None, "Contact name must be 100 characters or fewer."

    try:
        company_id = int_or_none(request.form.get("company_id"))
    except ValueError:
        return None, "Please select a valid company."

    if company_id is None or not company_exists(company_id):
        return None, "A valid company is required for a contact."

    email = opt(request.form.get("email"))
    if email and not EMAIL_RE.match(email):
        return None, "Please enter a valid email address."
    if email and len(email) > 100:
        return None, "Email must be 100 characters or fewer."

    phone = opt(request.form.get("phone"))
    if phone and len(phone) > 20:
        return None, "Phone must be 20 characters or fewer."

    data = (
        company_id,
        name,
        opt(request.form.get("title")),
        email,
        phone,
        opt(request.form.get("linkedin_url")),
        opt(request.form.get("notes"))
    )
    return data, None

@app.post("/contacts/add")
def add_contact():
    data, error = validate_contact_form()
    if error:
        flash(error, "danger")
        return redirect(url_for("contacts"))

    execute("""
        INSERT INTO contacts
        (company_id, contact_name, title, email, phone, linkedin_url, notes)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, data)

    flash("Contact added.", "success")
    return redirect(url_for("contacts"))

@app.route("/contacts/<int:item_id>/edit", methods=["GET", "POST"])
def edit_contact(item_id):
    contact = fetch_one("SELECT * FROM contacts WHERE contact_id=%s", (item_id,))
    companies_list = fetch_all(
        "SELECT company_id, company_name FROM companies ORDER BY company_name"
    )

    if not contact:
        flash("Contact not found.", "danger")
        return redirect(url_for("contacts"))

    if request.method == "POST":
        data, error = validate_contact_form()
        if error:
            flash(error, "danger")
            return redirect(url_for("edit_contact", item_id=item_id))

        execute("""
            UPDATE contacts
            SET company_id=%s, contact_name=%s, title=%s, email=%s,
                phone=%s, linkedin_url=%s, notes=%s
            WHERE contact_id=%s
        """, data + (item_id,))

        flash("Contact updated.", "success")
        return redirect(url_for("contacts"))

    return render_template(
        "contact_edit.html",
        contact=contact,
        companies=companies_list
    )

@app.post("/contacts/<int:item_id>/delete")
def delete_contact(item_id):
    if not fetch_one("SELECT contact_id FROM contacts WHERE contact_id=%s", (item_id,)):
        flash("Contact not found.", "danger")
        return redirect(url_for("contacts"))

    execute("DELETE FROM contacts WHERE contact_id=%s", (item_id,))
    flash("Contact deleted.", "success")
    return redirect(url_for("contacts"))

# -------------------- Job Match --------------------

@app.route("/job-match", methods=["GET", "POST"])
def job_match():
    results = []
    skills_text = ""

    if request.method == "POST":
        skills_text = request.form.get("skills", "")
        user_skills = {
            skill.strip().lower()
            for skill in skills_text.split(",")
            if skill.strip()
        }

        if not user_skills:
            flash("Enter at least one skill.", "danger")
            return render_template(
                "job_match.html",
                results=[],
                skills_text=skills_text
            )

        rows = fetch_all("""
            SELECT j.job_id, j.job_title, j.requirements, c.company_name
            FROM jobs j
            LEFT JOIN companies c ON j.company_id=c.company_id
            WHERE j.requirements IS NOT NULL
        """)

        for row in rows:
            requirements = row["requirements"]

            if isinstance(requirements, str):
                try:
                    requirements = json.loads(requirements)
                except json.JSONDecodeError:
                    requirements = {}

            required = (
                requirements.get("required_skills", [])
                if isinstance(requirements, dict)
                else []
            )

            if not isinstance(required, list):
                required = []

            # Treat skills as a set: duplicates must not distort the score.
            unique = {}
            for skill in required:
                if isinstance(skill, str) and skill.strip():
                    unique.setdefault(skill.strip().lower(), skill.strip())
            normalized = list(unique)
            required = list(unique.values())
            matched = [
                required[i]
                for i, skill in enumerate(normalized)
                if skill in user_skills
            ]
            missing = [
                required[i]
                for i, skill in enumerate(normalized)
                if skill not in user_skills
            ]

            percentage = (
                round(len(matched) * 100 / len(required))
                if required
                else 0
            )

            results.append({
                "job_id": row["job_id"],
                "job_title": row["job_title"],
                "company_name": row["company_name"],
                "required": required,
                "matched": matched,
                "missing": missing,
                "percentage": percentage
            })

        results.sort(
            key=lambda result: (-result["percentage"], result["job_title"].lower())
        )

    return render_template(
        "job_match.html",
        results=results,
        skills_text=skills_text
    )

# -------------------- Read-only record details --------------------

DETAILS = {
    "company": {
        "table": "companies", "title": "company_name",
        "query": "SELECT * FROM companies WHERE company_id=%s",
        "fields": [("company_name", "Company name", "text"), ("industry", "Industry", "text"),
                   ("website", "Website", "url"), ("city", "City", "text"),
                   ("state", "State", "text"), ("notes", "Notes", "text")],
    },
    "job": {
        "table": "jobs", "title": "job_title",
        "query": "SELECT j.*, c.company_name FROM jobs j LEFT JOIN companies c "
                 "ON j.company_id=c.company_id WHERE j.job_id=%s",
        "fields": [("job_title", "Job title", "text"), ("company_name", "Company", "company"),
                   ("job_type", "Employment type", "text"), ("date_posted", "Date posted", "text"),
                   ("salary_min", "Minimum annual salary", "money"),
                   ("salary_max", "Maximum annual salary", "money"),
                   ("job_url", "Job posting", "url"), ("requirements", "Requirements", "json")],
    },
    "application": {
        "table": "applications", "title": "job_title",
        "query": "SELECT a.*, j.job_title, j.company_id, c.company_name FROM applications a "
                 "JOIN jobs j ON a.job_id=j.job_id LEFT JOIN companies c "
                 "ON j.company_id=c.company_id WHERE a.application_id=%s",
        "fields": [("job_title", "Job", "job"), ("company_name", "Company", "company"),
                   ("application_date", "Application date", "text"), ("status", "Status", "status"),
                   ("resume_version", "Resume version", "text"),
                   ("cover_letter_sent", "Cover letter sent", "boolean"),
                   ("interview_data", "Interview details", "json")],
    },
    "contact": {
        "table": "contacts", "title": "contact_name",
        "query": "SELECT ct.*, c.company_name FROM contacts ct JOIN companies c "
                 "ON ct.company_id=c.company_id WHERE ct.contact_id=%s",
        "fields": [("contact_name", "Contact name", "text"), ("company_name", "Company", "company"),
                   ("title", "Job title", "text"), ("email", "Email", "text"),
                   ("phone", "Phone", "text"), ("linkedin_url", "LinkedIn", "url"),
                   ("notes", "Notes", "text")],
    },
}


@app.template_filter("pretty_json")
def pretty_json(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except ValueError:
            return value
    return json.dumps(value, indent=2, ensure_ascii=False)


@app.template_filter("external_url")
def external_url(value):
    """Links remain safe even when a URL was inserted outside the Flask forms."""
    try:
        parsed = urlsplit(value or "")
        return parsed.scheme in ("http", "https") and bool(parsed.hostname)
    except ValueError:
        return False


def record_detail(kind, item_id):
    config = DETAILS[kind]
    record = fetch_one(config["query"], (item_id,))
    if not record:
        abort(404)
    related = []
    if kind == "company":
        related = [
            {"label": "Jobs", "kind": "job", "name": "job_title", "id": "job_id",
             "rows": fetch_all("SELECT * FROM jobs WHERE company_id=%s ORDER BY job_title", (item_id,))},
            {"label": "Contacts", "kind": "contact", "name": "contact_name", "id": "contact_id",
             "rows": fetch_all("SELECT * FROM contacts WHERE company_id=%s ORDER BY contact_name", (item_id,))},
        ]
    elif kind == "job":
        related = [{"label": "Applications", "kind": "application", "name": "application_date", "id": "application_id",
                    "rows": fetch_all("SELECT * FROM applications WHERE job_id=%s "
                                      "ORDER BY application_date DESC, application_id DESC", (item_id,))}]
    return render_template("record_detail.html", kind=kind, record=record, config=config,
                           item_id=item_id, related=related)


@app.get("/companies/<int:item_id>")
def detail_company(item_id):
    return record_detail("company", item_id)


@app.get("/jobs/<int:item_id>")
def detail_job(item_id):
    return record_detail("job", item_id)


@app.get("/applications/<int:item_id>")
def detail_application(item_id):
    return record_detail("application", item_id)


@app.get("/contacts/<int:item_id>")
def detail_contact(item_id):
    return record_detail("contact", item_id)


@app.errorhandler(Error)
def db_error(error):
    app.logger.error("Database request failed: %s", error)
    return render_template(
        "error.html",
        message="The database could not complete this request. Check that MySQL is running, "
                "the schema has been imported, and DB_USER / DB_PASSWORD are configured."
    ), 500

@app.errorhandler(404)
def not_found(error):
    return render_template(
        "error.html",
        message="The requested page was not found."
    ), 404

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
