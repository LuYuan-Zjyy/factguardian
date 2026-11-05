# Contributing to FactGuardian

Thanks for taking the time to contribute! This guide keeps reviews fast.

## Ways to help

- **Bug reports** — open an issue using the bug template, including the document type, the endpoint, and the response you got.
- **Prompt / detection quality** — if the detector misses a conflict or raises a false one, a minimal reproducible document is worth more than a long description.
- **Providers** — new vision or search backends are welcome; keep them behind the existing service interfaces.
- **Docs and UI polish** — screenshots, wording, and small UX fixes are always appreciated.

## Development setup (without Docker)

```bash
# backend
cd backend
python -m venv .venv && . .venv/Scripts/activate    # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# frontend (second terminal)
cd frontend
npm install
npm run dev        # http://localhost:3000
```

Create a `.env` in the repository root from `.env.example`. **Never commit real keys** — see `SECURITY` below.

## Pull request checklist

1. One PR = one concern. Don't mix refactors with behaviour changes.
2. If you change detection logic, add or update a test document under `backend/test_data_*` and describe expected vs. actual output in the PR.
3. Keep the diff focused; avoid reformatting unrelated files.
4. Make sure the CI jobs pass (`backend-lint`, `frontend-build`).
5. Update `README.md` / `README.zh-CN.md` if user-facing behaviour changes.

## Commit messages

Short imperative subject, then *why* in the body. Examples:

```
detector: ignore numeric conflicts inside quoted citations
frontend: keep conflict highlight after re-analyze
```

## Security

- `.env` is git-ignored. Never commit API keys, tokens, or personal data.
- If you believe a secret was committed, open an issue **without quoting the secret** and rotate the key immediately.

## Code style

- Python: PEP 8, type hints on public functions, `ruff` clean for errors.
- JavaScript/React: functional components, hooks, no new global state unless necessary.

## License

By contributing you agree that your contributions are licensed under the [MIT License](LICENSE).
