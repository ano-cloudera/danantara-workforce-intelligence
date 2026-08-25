# Skill: cai-application-deployment

Deploy and troubleshoot the four Cloudera AI Applications.

## Rules
- Use the application-specific `run_cai.py`.
- Do not assume `__file__` exists in a CAI Application entrypoint; resolve the Application path
  from `CDSW_PROJECT_DIR`, the project working directory, or a checkout immediately below the
  working directory when CAI executes it as interpreter code.
- Keep the Qdrant launcher standalone when CAI interpreter execution exposes neither the checkout
  nor `CDSW_PROJECT_DIR`; its runtime may safely bootstrap under the interpreter working directory.
- Run native service binaries as child processes of the CAI Python engine, probe compatibility
  before startup, and preserve stdout/stderr so Application Logs expose the real failure.
- Resolve listener ports strictly as `CDSW_APP_PORT -> PORT -> local development default`.
- Bind every CAI Application to `127.0.0.1`; never hardcode a CAI exposed port.
- Configure cross-Application calls with `BACKEND_BASE_URL`, `QDRANT_BASE_URL`, and
  `OBSERVABILITY_BASE_URL`; never infer CAI hostnames or ports.
- Create project-local venvs rather than relying on system package installation.
- Keep secrets in hidden Application environment variables.
- Verify `/health` before wiring another app.
