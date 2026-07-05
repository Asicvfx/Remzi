# Remzi Project Status

Remzi is currently a local-first RAG MVP for chatting with uploaded documents.

## Current Stage

Stage 15 is complete.

## What Works

- Django REST backend with JWT authentication.
- Document upload for PDF, DOCX, and TXT files.
- Celery worker processing for text extraction and chunking.
- Local deterministic embeddings for MVP search.
- Authenticated document search across user-owned chunks.
- OpenAI-backed answers when `OPENAI_ANSWER_ENABLED=True`.
- Local extractive fallback when OpenAI is disabled.
- Persisted chat sessions and chat messages.
- Streaming chat answers through `POST /api/chats/{id}/ask/stream/`.
- Frontend workspace for login, upload, document selection, chats, answers, and citations.
- Frontend auto-refresh while documents are uploaded or processing.
- Friendly frontend errors for network, auth, validation, failed documents, and processing documents.

## Local URLs

- Frontend: `http://localhost:3000/`
- Backend API: `http://localhost:8000/`
- Swagger: `http://localhost:8000/api/docs/`
- OpenAPI schema: `http://localhost:8000/api/schema/`

## Verification

Latest verified checks:

- `python backend/manage.py test apps.common apps.users apps.documents apps.chunks apps.search apps.answers apps.chats`
- `npm run build` from `D:\RemziFrontendWorkspace`

## Not In Scope Yet

- Public deployment.
- Billing or multi-tenant organizations.
- Production object storage for uploaded files.
- Full observability, analytics, or admin dashboards.
- Advanced vector database integration.
