# Skill: cai-application-deployment

Deploy and troubleshoot the four Cloudera AI Applications.

## Rules
- Use the application-specific `run_cai.py`.
- Do not assume `__file__` exists in a CAI Application entrypoint; resolve the Application path
  from `CDSW_PROJECT_DIR` or the project working directory when CAI executes it as interpreter code.
- Resolve listener ports strictly as `CDSW_APP_PORT -> PORT -> local development default`.
- Bind every CAI Application to `127.0.0.1`; never hardcode a CAI exposed port.
- Configure cross-Application calls with `BACKEND_BASE_URL`, `QDRANT_BASE_URL`, and
  `OBSERVABILITY_BASE_URL`; never infer CAI hostnames or ports.
- Create project-local venvs rather than relying on system package installation.
- Keep secrets in hidden Application environment variables.
- Verify `/health` before wiring another app.
