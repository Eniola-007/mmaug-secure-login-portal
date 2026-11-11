# MMAUG High School Secure Login Portal

Production-oriented MVP for RFP `MMAUG-AIDB-RFP-002`.

## Architecture

- Public React + TypeScript landing page with Microsoft and email/password account paths
- FastAPI protected API with server-side role and account-status checks
- PostgreSQL application profiles and append-only audit events
- Microsoft Foundry role assistants grounded in a curated Azure Blob knowledge base,
  with deterministic pre-model guardrails and a safe fallback
- Azure App Service Plan, Application Gateway WAF_v2, Key Vault, Application Insights,
  and one approved user-assigned managed identity
- Terraform infrastructure and GitHub Actions deployment through OIDC

Deployment is infrastructure-first: the managed identity deploys the Web Apps and returns
the frontend URL; the Entra administrator then creates the SPA/API registrations and
configures MSAL without granting the deployment identity Microsoft Graph permissions.

Microsoft accounts use the identity platform `common` authority; non-Microsoft visitors
can create a password account whose Argon2id hash is stored separately. Authentication
does not grant portal access: every new account is inactive until an administrator assigns
and activates its PostgreSQL role. Microsoft identities are keyed by immutable
`tenant ID + object ID`. See
[docs/architecture.md](docs/architecture.md).

The MVP contains synthetic data only. It is not approved for real student data.

The application role comes from PostgreSQL after token validation. The frontend never
selects the authorization role, and the assistant receives only the role chosen by the
API. Reviewed assistant source material is in [`knowledge-base`](knowledge-base).

Self-registration never accepts a role. All new requests start as inactive Student
records; only the Administrator dashboard can activate an account or assign Teacher or
Administrator. The controlled first-admin procedure is documented in
[docs/first-administrator.md](docs/first-administrator.md).

The proposed public endpoint is
`https://mmaug-secure-portal.northeurope.cloudapp.azure.com`, reserved on Standard static
Public IP `68.219.97.185`. The solution uses managed identity and GitHub OIDC instead of
a client secret.

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

The updated RFP response is available as
[proposal source](docs/proposal-v4.md) and
[Version 4 PDF](MMAUG_Secure_Login_Portal_RFP_Response_v4_Single_Identity_WAF.pdf).
