# Security Notes

- Prefer CAI/enterprise SSO rather than custom username/password storage.
- Frontend identity propagation is based on trusted CAI headers when `AUTH_MODE=cai`.
- SQLite stores session/feedback state only.
- Gemini, Qdrant, NiFi, Impala and observability credentials are environment variables.
- Hide sensitive Cloudera AI environment variables in Application Settings.
- Avoid logging raw CVs, full prompts with PII, or document bodies to observability.
- Policy and candidate access must still be authorized at the Cloudera data layer.
- AI candidate recommendations require human review in this PoC.
