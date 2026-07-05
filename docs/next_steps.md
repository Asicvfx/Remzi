# Next Steps

This roadmap intentionally skips public deployment for now. Remzi should stay local-first until the product flow feels stable.

## Recommended Next Work

1. Improve chat UX.
2. Add document management polish.
3. Add local developer ergonomics.
4. Add observability for the worker and answer pipeline.
5. Prepare deployment only after the local product is comfortable to demo.

## Stage 16 Candidate: Chat UX Polish

- Add a clear "new answer is streaming" state on the ask button.
- Scroll to the newest answer automatically.
- Add copy buttons for answers and citations.
- Add a small "answer mode" badge for `openai` vs `local`.
- Add a "clear current chat" or "delete chat" action in the frontend.

## Stage 17 Candidate: Document Management

- Add delete document action to the frontend.
- Show chunk count and extracted text length more clearly.
- Show failed-document reasons in a compact expandable panel.
- Add a "re-upload" hint for failed files.

## Stage 18 Candidate: Developer Experience

- Add a local `Makefile` or PowerShell scripts for common commands.
- Add a one-command backend test runner.
- Add a one-command frontend build runner.
- Add sample `.txt` document under `docs/samples/` for demos.

## Stage 19 Candidate: Pipeline Observability

- Add simple logs around document processing duration.
- Add answer generation timing logs.
- Add worker health notes to README.
- Add admin list filters for failed and processing documents.

## Later, Not Today

- Public deployment.
- Hosted PostgreSQL and Redis.
- Production file storage.
- CI/CD.
- Real vector database.
- Multi-user organizations and billing.
