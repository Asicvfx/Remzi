# Remzi

Remzi is a portfolio-level RAG application. Stages 0-12 include the monorepo foundation, Docker environment, Django REST backend, JWT authentication, document upload APIs, Celery-based background processing, text extraction, document chunking, local embeddings, authenticated chunk search, OpenAI-powered answers with citations, a beginner-friendly frontend chat workspace, persisted chat history, automatic document processing polling, and a frontend typing effect for new answers.

## Current structure

```text
Remzi/
  backend/
  frontend/
  docker-compose.yml
  .env.example
  README.md
```

## Stage 0-12 features

- Monorepo layout for backend and frontend.
- Docker Compose with PostgreSQL, Redis, Django backend, and Celery worker.
- Django 5 + DRF backend with env-driven settings.
- JWT auth with register, login, refresh, and `me` endpoints.
- Document upload, list, detail, and delete APIs.
- Celery task dispatch after document upload.
- Text extraction for `.txt`, `.pdf`, and `.docx` files.
- Document status transition from `uploaded` to `processing`, then `ready` or `failed`.
- Text preview, extracted text length, and chunk count in document API responses.
- Document chunks generated from extracted text.
- Local deterministic embeddings generated for each document chunk.
- Authenticated search over the current user's chunks.
- Answer endpoint with citations.
- Optional OpenAI answer generation for `/api/ask/` with local fallback.
- Persisted chat sessions and saved question/answer history.
- Frontend auto-refreshes document statuses while files are uploaded or processing.
- Frontend shows newly generated answers with a typing effect while keeping saved history instant.
- Frontend workspace for login, document upload, document selection, chat history, questions, answers, and citations.
- Swagger UI at `/api/docs/`.
- Basic auth, document pipeline, chunking, search, and answer tests.

## Backend endpoints

Auth:
- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `POST /api/auth/token/refresh/`
- `GET /api/auth/me/`

Documents:
- `POST /api/documents/upload/`
- `GET /api/documents/`
- `GET /api/documents/{id}/`
- `GET /api/documents/{id}/chunks/`
- `DELETE /api/documents/{id}/`

Search, answers, and chats:
- `POST /api/search/`
- `POST /api/ask/`
- `GET /api/chats/`
- `POST /api/chats/`
- `GET /api/chats/{id}/`
- `DELETE /api/chats/{id}/`
- `GET /api/chats/{id}/messages/`
- `POST /api/chats/{id}/ask/`

Docs:
- `GET /api/schema/`
- `GET /api/docs/`

## Local setup

1. Copy env file:

```bash
cp .env.example .env
```

On Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Optional: enable OpenAI answers in `.env`:

```env
OPENAI_API_KEY=your_api_key_here
OPENAI_ANSWER_ENABLED=True
LLM_MODEL=gpt-5.5
```

If OpenAI is not enabled, Remzi still works with local extractive answers.

2. Start the backend stack:

```bash
docker compose up --build
```

3. Start the frontend from D:

```powershell
cd D:\RemziFrontendWorkspace
npm run dev
```

4. Open the apps:

- Frontend workspace: `http://localhost:3000/`
- Backend API: `http://localhost:8000/`
- Swagger: `http://localhost:8000/api/docs/`
- Schema: `http://localhost:8000/api/schema/`

## How to use the frontend

1. Open `http://localhost:3000/`.
2. Login with your Remzi username and password.
3. Upload a `.pdf`, `.docx`, or `.txt` file.
4. Wait while Remzi auto-refreshes the document status until it becomes `Ready`.
5. Select a document or choose all documents.
6. Ask a question and watch the new answer appear gradually with citations.
7. Reopen the chat later; saved questions and answers remain in history.

If the answer response says `OpenAI answer`, the model generated the answer from retrieved citations. If it says `Local fallback`, Remzi answered with the built-in extractive mode.

## Run backend without Docker

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r backend/requirements.txt
```

3. Apply migrations:

```bash
python backend/manage.py migrate
```

4. Start the server:

```bash
python backend/manage.py runserver
```

5. In another terminal, start the worker from the `backend/` directory:

```bash
cd backend
celery -A config worker -l info
```

## Run frontend without Docker

The local `frontend` folder is a junction to `D:\RemziFrontendWorkspace`, so start dev from the real D path to avoid Windows junction path issues:

```powershell
cd D:\RemziFrontendWorkspace
npm run dev
```

The frontend expects the backend at `http://localhost:8000/api`. You can override it with `NEXT_PUBLIC_API_URL`.

## How to test in Swagger or Postman

### Register

`POST /api/auth/register/`

```json
{
  "username": "remzi-user",
  "email": "user@example.com",
  "password": "StrongPass123",
  "password_confirm": "StrongPass123",
  "first_name": "Remzi",
  "last_name": "User"
}
```

### Login

`POST /api/auth/login/`

```json
{
  "username": "remzi-user",
  "password": "StrongPass123"
}
```

Copy the `access` token and authorize Swagger with the token value. Swagger will prepend `Bearer` automatically.

### Upload a document

`POST /api/documents/upload/`

Use `multipart/form-data` with:
- `file`: a `.pdf`, `.docx`, or `.txt` file
- `title`: optional custom title

After upload, open `GET /api/documents/` or `GET /api/documents/{id}/` and confirm:
- `status` becomes `ready` when text extraction succeeds
- `status` becomes `failed` with `error_message` when no text can be extracted
- `extracted_text_length` is greater than `0` for successful extraction
- `chunk_count` is greater than `0` for successful extraction
- `text_preview` shows the beginning of extracted text

### View document chunks

`GET /api/documents/{id}/chunks/`

Use the same document `id` that returned `status: "ready"`. A successful response returns an array of chunks. Each chunk contains:
- `chunk_index`: chunk order inside the document
- `text`: the chunk text
- `token_count`: approximate word-based token count
- `embedding_model`: currently `local-hashing-v1`
- `embedding_dimensions`: currently `64`

### Search your documents

`POST /api/search/`

```json
{
  "query": "what is this document about",
  "limit": 5,
  "document_id": 1
}
```

`document_id` is optional. If omitted, Remzi searches across all documents owned by the authenticated user.

### Ask a question

`POST /api/ask/`

```json
{
  "question": "what does this document say about work experience",
  "limit": 5,
  "document_id": 1
}
```

A successful response returns an answer and citations. If `OPENAI_ANSWER_ENABLED=True` and `OPENAI_API_KEY` is set, Remzi uses OpenAI; otherwise it falls back to the local extractive answer composer:

```json
{
  "question": "what does this document say about work experience",
  "answer": "Based on the retrieved document chunks: ...",
  "answer_mode": "openai",
  "model": "gpt-5.5",
  "document_id": 1,
  "citations": [
    {
      "document_id": 1,
      "document_title": "My first document",
      "chunk_id": 1,
      "chunk_index": 0,
      "score": 0.42,
      "text": "Relevant chunk text preview..."
    }
  ]
}
```

The answer generator is provider-aware. It returns `answer_mode: "openai"` when OpenAI produces the answer, and `answer_mode: "local"` when Remzi uses the built-in extractive fallback. Answers are still grounded in retrieved citations.

## Tests

Run backend tests with:

```bash
python backend/manage.py test apps.common apps.users apps.documents apps.chunks apps.search apps.answers apps.chats
```

Run frontend build checks with:

```powershell
cd D:\RemziFrontendWorkspace
npm run build
```

## Changed files in Stage 12

- Added a frontend typing effect for newly saved chat answers.
- Added a blinking answer cursor and subtle active-answer styling.
- Updated the homepage hero and empty state for Stage 12.
- Updated README instructions for Stage 12.

## Next stage

Stage 13 can add true backend/OpenAI streaming or start cleaning the production UI.









