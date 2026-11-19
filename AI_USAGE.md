# AI Usage Documentation

## Tools Used

- Claude (Anthropic, claude.ai chat) for schema review, job match code review, README/setup review, and generating a corrected schema.sql and this documentation file.

Claude was used as a reviewer. I uploaded the project repository and Claude read schema.sql, database.py, app.py, README.md, and requirements.txt. Claude did not edit app.py, database.py, the templates, or the CSS.

## Key Prompts

1. "Here is my MySQL schema for a job application tracker with 4 tables. Check my foreign keys, ON DELETE behavior, and JSON column usage. List problems only, don't rewrite it."
2. "Review my function for edge cases like empty lists and case sensitivity."
3. "Review this README.md and requirements.txt. Could someone clone this repo and run it from scratch? What setup steps are missing?"
4. A request for a corrected schema.sql and for this AI_USAGE.md, made after reviewing the findings and the Project Specification.

## What Worked

- **Schema review:** Claude found a mismatch between the schema and the Flask validation: `applications.job_id` was nullable with `ON DELETE SET NULL`, but the app requires an existing job, so deleting a job left orphaned applications that could not be edited. It also found contacts that could exist without a company, no database-level check on the salary range or JSON shape, `status` and `cover_letter_sent` allowing NULL, no unique company names, and a schema.sql that could not be safely re-run.
- **Job Match review:** Claude confirmed that duplicates, non-string skills, blank input, and NULL requirements are handled, and flagged that Python's `round()` rounds half to even (12.5% displays as 12%), that jobs with no required skills score 0% rather than "not applicable," that matching only uses `strip().lower()` (no `casefold()` or whitespace/punctuation normalization), and that input is only split on commas.
- **README review:** Claude found that AI_USAGE.md and the required demo video were missing from the repository, that the README ended with leftover assistant wording, that database.py defaults the password to a placeholder, and that the README lacked a warning about importing the schema twice.
- **Spec comparison:** Claude checked the repository against the Project Specification and noted that the Read requirement mentions "lists and detail views" while the app has lists and edit pages only, and that the specification's Job Match example shows counts such as "100% (3/3 skills)" while the app shows the percentage with matched and missing skill lists.

## What You Changed

- Claude's corrected schema.sql intentionally goes beyond the base schema in the Project Specification. It makes `applications.job_id` and `contacts.company_id` NOT NULL with `ON DELETE CASCADE`, keeps `jobs.company_id` as `ON DELETE SET NULL`, adds CHECK constraints (salary range, `requirements` must be a JSON object), makes `status` and `cover_letter_sent` NOT NULL, adds a unique constraint on `company_name`, and drops and recreates the tables so the script can be re-run (which erases existing data).
- These schema changes affect other parts of the project: the README statements about delete behavior, the delete confirmation text, and the add/edit company routes (which should handle the duplicate-name error) have to match the new schema.
- The Job Match, README, and requirements.txt reviews produced lists of issues only; no code from those reviews was written by Claude.

## Lessons Learned

- Asking for a review ("list problems only") instead of a rewrite keeps the design decisions with me and makes the AI's output easier to check.
- Reviewing across files caught a mismatch (schema `SET NULL` versus the Flask rule that applications require a job) that is easy to miss when looking at each file alone.
- AI changes to a schema have consequences elsewhere (README claims, delete behavior, error handling), so every suggestion has to be checked against the rest of the code and tested before it is kept.
- Giving the AI the real files and the course specification produced specific, checkable feedback instead of generic advice.
