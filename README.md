# MMAUG High School Secure Login Portal

Production-oriented MVP for RFP `MMAUG-AIDB-RFP-002`.

## Architecture

- React + TypeScript frontend with Microsoft Entra ID sign-in
- FastAPI protected API with server-side role and account-status checks
- PostgreSQL application profiles and append-only audit events
- Azure App Service, Key Vault, Application Insights, and managed identity
- Terraform infrastructure and GitHub Actions deployment through OIDC

The MVP contains synthetic data only. It is not approved for real student data.

## Local development

Prerequisites: Python 3.11+, Node.js 20+, and Docker Desktop for PostgreSQL.

```powershell
Copy-Item .env.example .env
docker compose up -d postgres
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".\backend[dev]"
$env:PYTHONPATH = ".\backend"
.\.venv\Scripts\python -m app.seed
.\.venv\Scripts\python -m uvicorn app.main:app --reload --app-dir backend
```

In another terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Local development authentication is disabled by default. Set `ALLOW_DEV_AUTH=true`
only on a developer workstation and use one of the eight seeded email addresses in
the `X-Dev-User` header. Production refuses this mode.

## Verification

```powershell
.\.venv\Scripts\python -m pytest backend/tests
Set-Location frontend
npm run lint
npm run build
```

See [docs/deployment.md](docs/deployment.md) for Azure and OIDC setup and
[docs/security.md](docs/security.md) for the security boundary.
