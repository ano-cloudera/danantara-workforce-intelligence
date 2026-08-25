# Skill: cai-application-deployment

Deploy and troubleshoot the four Cloudera AI Applications.

## Rules
- Use the application-specific `run_cai.py`.
- Use `CDSW_APP_PORT` first, with local fallback only for development.
- Create project-local venvs rather than relying on system package installation.
- Keep secrets in hidden Application environment variables.
- Verify `/health` before wiring another app.
