# Testing report

## Automated checks completed

Run `python -m unittest discover -v` from the project root after installing requirements.

Thirteen test groups cover:

1. All six main pages with empty/populated data and accessible named form controls.
2. Create, read, edit, and delete for all four entities using route requests and persisted test data.
3. Invalid fields rejected before a write, including negative/oversized salaries, missing FKs, malformed JSON, NaN, invalid skill arrays, long fields, invalid URLs, and invalid dates/enums/email.
4. Matching at 0%, partial percentages, and 100%, including case/whitespace/duplicate normalization.
5. Missing record redirects and a rendered 404 page.
6. Company deletion cascading to contacts while preserving jobs with NULL company references; job deletion cascading to applications in the test double.
7. HTML escaping and complete status filter options.
8. A rendered database error page with an HTTP 500 response.
9. Dedicated detail pages for all four tables, with related links, JSON, zero salary, and 404s.
10. Escaped detail content and safe external URL rendering.
11. Unique company names enforced during both create and edit.
12. Required company selection in contact forms and server validation.
13. Delete confirmation messages accurately describing cascading deletions.

The tests use an in-memory SQLite test double to execute the route SQL with parameter placeholders adapted. This verifies application behavior, not MySQL JSON, ENUM, server configuration, or MySQL transaction semantics.

## Browser checks completed

A temporary QA harness outside this deliverable rendered the real Flask templates with fictional records:

- Desktop dashboard, application table, and Job Match inspected.
- Application search filtered to DataCo (1 of 3 records).
- Combining that search with Interview status produced 0 of 3 records and the correct empty message.
- Python, SQL, Flask produced a 100% Developer match and 33% partial matches.
- Dashboard inspected at 390px width; the page had no horizontal overflow. Navigation/table areas may scroll horizontally inside their own containers.
- Scroll changed the decorative artwork transform; CSS/JS include reduced-motion handling.

Screenshots in `docs/` are from that fixture preview, not proof of MySQL execution.

## Version 2 browser verification

The dedicated detail pages and their related links are checked separately with fictional test data. The production database layer remains MySQL; the preview harness is outside the repository.

## Required live checks before submitting

- Import schema.sql into fresh MySQL 8 and inspect all four native table definitions and foreign keys.
- Set database credentials, run Flask, and repeat CRUD against MySQL. Restart Flask to verify persistence.
- Verify native JSON storage and enum values with SELECT / SHOW CREATE TABLE.
- Verify parent deletion behavior in MySQL with disposable records.
- Use valid and invalid data for both create and edit forms.
- On Job Match, compare Python, SQL (67%) and Python, SQL, Flask (100%) for the seeded Software Developer job.
- Enable the OS/browser reduced-motion preference and verify artwork stays still.
- Fresh-clone the GitHub repository into another folder, install requirements, configure MySQL, and follow README.md without relying on files outside the repository.
- Record and upload the required video; confirm it is playable from the repository.

The full specification was supplied and reviewed for this version. Live MySQL execution, a fresh-clone MySQL setup, and the video remain required checks.
