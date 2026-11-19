# Rubric & Submission Checklist

Use this checklist before submitting the COP4751 Job Application Tracker.

## Database — 25 points
- [ ] `companies` table exists.
- [ ] `jobs` table exists.
- [ ] `applications` table exists.
- [ ] `contacts` table exists.
- [ ] `jobs.company_id` is a foreign key to `companies.company_id`.
- [ ] `applications.job_id` is a foreign key to `jobs.job_id`.
- [ ] `contacts.company_id` is a foreign key to `companies.company_id`.
- [ ] `jobs.requirements` uses the MySQL `JSON` type.
- [ ] `applications.interview_data` uses the MySQL `JSON` type.
- [ ] Run `schema.sql` successfully on a fresh MySQL database.

## CRUD — 25 points
For each table, demonstrate all four actions:
- [ ] Companies: Create
- [ ] Companies: Read/List
- [ ] Companies: Update
- [ ] Companies: Delete
- [ ] Jobs: Create
- [ ] Jobs: Read/List
- [ ] Jobs: Update
- [ ] Jobs: Delete
- [ ] Applications: Create
- [ ] Applications: Read/List
- [ ] Applications: Update
- [ ] Applications: Delete
- [ ] Contacts: Create
- [ ] Contacts: Read/List
- [ ] Contacts: Update
- [ ] Contacts: Delete
- [ ] Show validation by intentionally entering at least one invalid value and confirming the app displays an error.

## UI — 15 points
- [ ] Navigation works on every page.
- [ ] Each list has a View details link to a dedicated read-only page.
- [ ] Related records link to their detail pages.
- [ ] Company names are unique; contacts require an existing company.
- [ ] Company deletion removes contacts; job deletion removes applications.
- [ ] Back up needed data before importing the supplied schema reset script.
- [ ] Forms are readable and consistently styled.
- [ ] Tables are readable.
- [ ] Flash messages appear after create/update/delete.
- [ ] Delete actions ask for confirmation.
- [ ] Test the interface at normal desktop width.
- [ ] Test at a narrow/mobile browser width.

## Job Match — 15 points
- [ ] Add jobs whose `requirements` JSON includes a `required_skills` array.
- [ ] Enter skills on the Job Match page.
- [ ] Confirm jobs are sorted from highest to lowest percentage.
- [ ] Confirm the percentage is correct.
- [ ] Confirm matched skills are displayed.
- [ ] Confirm missing skills are displayed.
- [ ] Demonstrate a 100% match.
- [ ] Demonstrate a partial match.

Example requirements JSON:
```json
{
  "required_skills": ["Python", "SQL", "Flask"],
  "preferred_skills": ["Docker", "AWS"],
  "remote_option": true
}
```

## Code / GitHub — 10 points
- [ ] Push the project to GitHub.
- [ ] Keep the repository public or add the instructor as collaborator.
- [ ] Do not commit database passwords.
- [ ] Use several meaningful commits rather than one final upload.
- [ ] Confirm `README.md` explains setup and execution.
- [ ] Confirm code is readable and organized.

Suggested meaningful commit sequence:
1. `Create MySQL schema and relationships`
2. `Add database connection helper`
3. `Implement companies and jobs CRUD`
4. `Implement applications and contacts CRUD`
5. `Add server-side validation`
6. `Add dashboard statistics`
7. `Implement JSON job match feature`
8. `Polish responsive UI`
9. `Add README and AI usage documentation`
10. `Final testing and cleanup`

Only use commit messages that truthfully describe work you actually performed.

## AI Documentation — 10 points
- [ ] `AI_USAGE.md` names the AI tools used.
- [ ] It includes important prompts.
- [ ] It explains what worked well.
- [ ] It explains what was modified or verified.
- [ ] It includes lessons learned.

## Final Submission
- [ ] GitHub repository link ready.
- [ ] 3–7 minute demonstration video recorded.
- [ ] Actual recorded video file committed/pushed to GitHub and confirmed playable.
- [ ] Follow `VIDEO_GUIDE.md` to demonstrate client, Flask server, and MySQL database.
- [ ] Review `TESTING.md` and complete its live MySQL and fresh-clone checks.
- [ ] Complete the student reflection in `AI_USAGE.md` with your own work and learning.
- [ ] `README.md` included.
- [ ] `AI_USAGE.md` included.
- [ ] `schema.sql` included.
- [ ] App runs after a fresh clone and setup.
