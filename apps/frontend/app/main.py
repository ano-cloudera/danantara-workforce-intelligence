import os
from pathlib import Path

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
STATIC = HERE / "static"
configured_backend = os.getenv("BACKEND_BASE_URL", "").strip().rstrip("/")
BACKEND = configured_backend or (None if os.getenv("CDSW_APP_PORT") else "http://127.0.0.1:8000")
DEMO_USER = os.getenv("DEMO_USER", "demo.hr@danantara.local")
CDV_URL = os.getenv("CDV_DASHBOARD_URL", "")

app = FastAPI(title="Danantara Workforce Intelligence Frontend")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/health")
def health():
    return {"status": "ok", "service": "frontend", "backend": BACKEND or "not-configured"}


@app.get("/config.js")
def config_js():
    body = f"window.APP_CONFIG={{cdvDashboardUrl:{CDV_URL!r}}};"
    return Response(content=body, media_type="application/javascript")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.api_route("/api-proxy/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy(path: str, request: Request):
    if not BACKEND:
        return JSONResponse(
            {"detail": "BACKEND_BASE_URL is required in Cloudera AI"}, status_code=503
        )
    user = (
        request.headers.get("REMOTE-USER") or request.headers.get("X-Forwarded-User") or DEMO_USER
    )
    headers = {"X-User-Id": user}
    content_type = request.headers.get("content-type")
    if content_type:
        headers["content-type"] = content_type
    body = await request.body()
    url = f"{BACKEND}/api/v1/{path}"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.request(
                request.method, url, params=request.query_params, content=body, headers=headers
            )
        return Response(
            content=resp.content,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type"),
        )
    except Exception as exc:
        return JSONResponse({"detail": f"Backend unavailable: {exc}"}, status_code=502)
