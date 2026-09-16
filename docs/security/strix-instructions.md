Authorized security test of Forge LMS, a local development instance owned by the tester. Do not target any other host.

App: Django REST API at http://host.docker.internal:8000/api/v1/ (OpenAPI at /api/schema/, Swagger at /api/docs/) and React frontend at http://host.docker.internal:5174.
Auth: POST /api/v1/auth/token/ with {"email","password"} returns {access, refresh}; send "Authorization: Bearer <access>".
Note: 5 failed logins lock an email for 15 minutes, so avoid brute-forcing the accounts below.

Test accounts (fill in passwords locally from user.md; never commit them):
- admin: superadmin@forge.local / <password>
- faculty: teacher@forge.local / <password>
- student: student@forge.local / <password>
- second student for IDOR checks: student1@forge.local / <password>

Focus:
1. Broken access control and IDOR between student/faculty/admin roles: courses, enrollments, assignments and submissions, exams, attempts, results, coding problems, code submissions, users, and audit logs.
2. Authentication and session handling: token revocation, refresh rotation, forced password change, and the one-time links at /auth/password/set/ and /auth/password/forgot/.
3. Signed download links at /api/v1/files/<token>/<name>: forgery, expiry, path traversal, and whether private files leak from /media/.
4. Exam logic: answering after the deadline, touching another student's attempt, and seeing answers or results before release.
5. Upload handling and stored XSS in course content, announcements, and file names.
6. Code runner abuse: size limits, throttles, and leakage of hidden test cases. Judge0 is not running, so a 503 is expected.

Do not run denial-of-service or high-volume load tests. Report each finding with reproduction steps and the affected endpoint.
