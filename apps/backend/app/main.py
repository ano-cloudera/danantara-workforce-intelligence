import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import build_router
from app.config import get_settings
from app.services.data_gateway import DataGateway
from app.services.document_ingestion import DocumentIngestionService
from app.services.gemini_service import GeminiService
from app.services.guardrails_service import GuardrailsService
from app.services.observability import ObservabilityClient
from app.services.policy_fallback import PolicyFallback
from app.services.qdrant_service import QdrantService
from app.services.session_store import SessionStore

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

obs = ObservabilityClient(settings)
gemini = GeminiService(settings, obs)
store = SessionStore(settings)
data = DataGateway(settings, obs)
qdrant = QdrantService(settings, gemini, obs)
guardrails = GuardrailsService(settings, obs)
policy_fallback = PolicyFallback(settings)
ingestion = DocumentIngestionService(settings, qdrant, store, obs)

services = {
    'obs': obs, 'gemini': gemini, 'store': store, 'data': data, 'qdrant': qdrant,
    'guardrails': guardrails, 'policy_fallback': policy_fallback, 'ingestion': ingestion,
}

app = FastAPI(title='Danantara Workforce Intelligence API', version='0.1.0')
origins = ['*'] if settings.cors_origins.strip() == '*' else [x.strip() for x in settings.cors_origins.split(',') if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False, allow_methods=['*'], allow_headers=['*'])
app.include_router(build_router(services, settings), prefix=settings.api_prefix)

@app.get('/health')
def root_health():
    return {'status': 'ok', 'service': 'backend'}
