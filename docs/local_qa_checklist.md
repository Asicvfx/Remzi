# Local QA Checklist

Use this checklist before showing Remzi or continuing development.

## 1. Start Services

From the repository root:

```powershell
docker compose up --build
```

From the frontend workspace:

```powershell
cd D:\RemziFrontendWorkspace
npm run dev
```

Expected:

- Backend responds at `http://localhost:8000/api/docs/`.
- Frontend opens at `http://localhost:3000/`.
- Worker logs show document processing activity after uploads.

## 2. Authentication

- Open the frontend.
- Login with the local test user.
- If login fails, use Swagger to register or login again.
- If frontend says the token expired, login again.

Expected:

- Account panel appears.
- Upload, Chats, and Documents sections become visible.

## 3. Document Upload

- Upload a `.txt`, `.pdf`, or `.docx` file.
- Wait for auto-refresh.

Expected:

- New document appears in the Documents list.
- Status moves from `uploaded` or `processing` to `ready`.
- Failed documents show a readable error message.

## 4. Ask Flow

- Select a `ready` document.
- Ask a question about its content.

Expected:

- A temporary streaming answer card appears.
- Answer text arrives progressively.
- Final answer is saved in chat history.
- Citations are shown under the answer.

## 5. Error Handling

Check these cases when changing frontend or API code:

- Backend stopped: frontend explains that `localhost:8000` is unavailable.
- Expired token: frontend clears session and asks for login.
- Processing document: ask button is blocked and user sees a Ready-status hint.
- Failed document: frontend shows the document error and blocks asking.

## 6. Verification Commands

Run backend tests:

```powershell
python backend\manage.py test apps.common apps.users apps.documents apps.chunks apps.search apps.answers apps.chats
```

Run frontend build:

```powershell
cd D:\RemziFrontendWorkspace
npm run build
```
