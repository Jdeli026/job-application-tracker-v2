# Required demo video: target 5 minutes 45 seconds

Record the actual execution with MySQL connected. This guide is not the video. Narration is optional. Keep credentials out of the recording.

| Time | Show |
| --- | --- |
| 0:00-0:35 | Repository files, README setup, then MySQL's four tables. Show foreign keys and native JSON columns with SHOW CREATE TABLE. |
| 0:35-0:55 | Start Flask, show server output, open the dashboard. |
| 0:55-1:35 | Companies: create a temporary company, list it, open View details, edit it, show updated values. |
| 1:35-2:15 | Jobs: create a job linked to that company, include required_skills JSON, open View details, then edit it. |
| 2:15-2:55 | Applications: create one linked to the job, open View details and edit its status and interview JSON. Show search/status filters. |
| 2:55-3:35 | Contacts: create a linked contact, open View details, then edit it. Demonstrate a validation error. |
| 3:35-4:15 | Job Match: show Python, SQL at 67% and Python, SQL, Flask at 100% for a job requiring those 3 skills. Point out matched/missing skills. |
| 4:15-4:50 | Show saved records and JSON values directly in MySQL, confirming frontend/server/database work together. |
| 4:50-5:20 | Delete the disposable application/contact/job/company using the UI, showing confirmation and updated lists. |
| 5:20-5:45 | Show dashboard counts, mobile layout, subtle header parallax, AI_USAGE.md, and repository commit history. |

Save the recording as `demo.mp4` (or another playable video file) and commit/push the actual file. For a large video, compress it or use Git LFS with GitHub's supported upload limits. Confirm the instructor can obtain and play the file from the repository. Submit the repository URL.

The course instructions state that a missing video means the project will not be graded.

The supplied schema resets all four tables. Import it before recording and keep data you need backed up. Demonstrate cascade deletion only with disposable records: company deletion removes its contacts, and job deletion removes its applications. AI_USAGE.md is intentionally withheld from the new repository for now and must be completed and committed before submission.
