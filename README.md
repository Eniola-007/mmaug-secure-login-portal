# MMAUG High School Secure Login Portal

Secure, role-aware school portal and Microsoft Foundry assistant built for RFP
`MMAUG-AIDB-RFP-002`.

> **Educational-use caveat:** The MMAUG Secure Login Portal is a solution built as
> part of the Malta Microsoft AI User Group (MMUAG) AI & DevOps Fundamentals
> Bootcamp 2026. The solution is for demo/educational purposes and is not to be
> adopted as a production-ready system.

The development portal is live at
[`https://app-mmaug-development-web-gkt6d.azurewebsites.net`](https://app-mmaug-development-web-gkt6d.azurewebsites.net).
It uses synthetic demonstration data only. Microsoft sign-in remains pending the
tenant administrator's SPA/API app registrations; verified local-email accounts can
be used for the current demonstration.

## Contents

- [What is working](#what-is-working)
- [Where the agents are integrated](#where-the-agents-are-integrated)
- [Architecture](#architecture)
- [Microsoft services and communication paths](#microsoft-services-and-communication-paths)
- [Identity, permissions and secrets](#identity-permissions-and-secrets)
- [How a portal request works](#how-a-portal-request-works)
- [How an assistant request works](#how-an-assistant-request-works)
- [Deploy from start to finish](#deploy-from-start-to-finish)
- [Update the knowledge base](#update-the-knowledge-base)
- [Verification](#verification)
- [Screenshot placement](#screenshot-placement)
- [Security and production best practices](#security-and-production-best-practices)
- [Supporting documentation](#supporting-documentation)

## What is working

| Capability | Current state |
|---|---|
| Public landing page and assistant drawer | Live |
| Local sign-up, email verification and password recovery | Live |
| Administrator invitation, approval, role assignment and deletion | Live |
| Student, Teacher and Administrator dashboards | Live |
| PostgreSQL role and audit-event persistence | Live on private networking |
| Four Microsoft Foundry agents | Running: Visitor, Student, Teacher and Administrator |
| Role-isolated Foundry File Search | Provisioned and directly smoke-tested for all four agents |
| Website-to-Foundry invocation | Verified on 14 November 2026; public endpoint returned `mode: foundry` |
| Managed-identity runtime authentication | Verified with `id-mmaug-secure-login-portal` |
| Microsoft Entra browser sign-in | Pending tenant-admin SPA/API registrations and redirect URI |
| Application Gateway/WAF/custom DNS | Not deployed and not shown as current architecture |

The latest direct Foundry tests proved that each named agent could answer from its
own indexed knowledge. A separate live App Service test then called
`POST /api/agent/public` and received the Visitor agent's grounded response with
`mode: "foundry"`.

## Where the agents are integrated

The assistant is not only configured in the Foundry portal; it is connected to the
website in two user journeys.

### Public landing page

- The **Ask MMAUG** navigation link opens the public assistant area.
- The landing page explains what the assistant can and cannot do.
- A fixed **Ask MMAUG** button in the bottom-right opens a slide-out chat drawer.
- Questions are sent to `POST /api/agent/public`.
- The server always selects `mmaug-visitor`; the browser cannot request a more
  privileged agent.

Implementation references:

- UI request: [`frontend/src/App.tsx`](frontend/src/App.tsx#L138)
- Public navigation and assistant story: [`frontend/src/App.tsx`](frontend/src/App.tsx#L154)
- Bottom-right launcher: [`frontend/src/App.tsx`](frontend/src/App.tsx#L184)
- Public API orchestration: [`backend/app/routers/agents.py`](backend/app/routers/agents.py#L72)

### Signed-in dashboards

- Student, Teacher and Administrator workspaces include **My assistant** in the
  left navigation.
- Every dashboard also has a bottom-right **Ask MMAUG** launcher and slide-out chat.
- Questions are sent to `POST /api/agent/message` with the user's access token.
- FastAPI validates the session, reads the active role from PostgreSQL and maps that
  role to exactly one of `mmaug-student`, `mmaug-teacher` or `mmaug-admin`.
- The model cannot approve users, change roles, delete records or perform another
  privileged action.

Implementation references:

- Signed-in assistant request: [`frontend/src/App.tsx`](frontend/src/App.tsx#L387)
- **My assistant** navigation: [`frontend/src/App.tsx`](frontend/src/App.tsx#L401)
- Signed-in launcher: [`frontend/src/App.tsx`](frontend/src/App.tsx#L427)
- Role-to-agent selection: [`backend/app/routers/agents.py`](backend/app/routers/agents.py#L132)
- Deterministic guardrails: [`backend/app/agent_guardrails.py`](backend/app/agent_guardrails.py)

<!-- Screenshot: docs/screenshots/06-public-assistant-drawer.png
Caption: Public landing-page Ask MMAUG launcher and visitor chat drawer. -->

<!-- Screenshot: docs/screenshots/07-role-dashboard-assistant.png
Caption: Signed-in role dashboard showing My assistant and the chat drawer. -->

## Architecture

![Current Microsoft-style Azure architecture](docs/architecture-current.svg)

The application and data tier remain in **North Europe**. The active Microsoft
Foundry account, project, model and agents are in **Sweden Central**. The model uses
the EU `DataZoneStandard` deployment type. The old North Europe Foundry project was
deleted and is not part of the current design.

The current ingress is direct App Service HTTPS. There is no Application Gateway,
WAF or custom-DNS hop in the deployed path.

## Microsoft services and communication paths

| Service | What it does here | How it communicates |
|---|---|---|
| Microsoft Entra ID | Issues identity tokens and hosts the managed-identity service principal. Future SPA/API registrations will enable Microsoft browser sign-in. | Browser uses MSAL after app registration; App Service obtains managed-identity tokens without a stored password. |
| User-assigned managed identity | Single approved deployment/runtime identity: `id-mmaug-secure-login-portal`. | GitHub exchanges an OIDC token for Azure access; API App Service requests Entra tokens for Foundry and Azure services. |
| Azure App Service Plan | Linux B1 compute shared by frontend and API. | Hosts both App Services inside the resource group. |
| Frontend Azure App Service | Serves the React/TypeScript landing page, authentication screens and role dashboards. | Browser connects over HTTPS; frontend calls the API HTTPS endpoint. |
| API Azure App Service | Runs FastAPI and enforces authentication, status, database role, rate limits, audit and agent routing. | HTTPS from frontend; private TLS to PostgreSQL; managed-identity calls to Foundry and Azure services. |
| Azure Database for PostgreSQL Flexible Server | Stores users, role assignments, verification state, invitations, audit events and rate-limit records. | API reaches port 5432 through VNet integration and private DNS; the database has no public endpoint. |
| Azure Virtual Network and subnets | Keeps the PostgreSQL route private. | API integrates with the App Service subnet; PostgreSQL uses a delegated database subnet. |
| Azure Private DNS | Resolves the private PostgreSQL hostname from the VNet. | Linked to the VNet and used by the API connection string. |
| Azure Key Vault | Holds the PostgreSQL URL and local JWT signing value used through App Service references. | App Service resolves Key Vault references using the approved user-assigned identity. |
| Azure Communication Services Email | Sends account verification, invitation, recovery and administrator notification email. | API calls the ACS email endpoint; links return users to the frontend. |
| Azure Storage account — knowledge | Keeps a private reviewed copy of the Markdown knowledge base. | GitHub uploads approved files during deployment; Foundry provisioning indexes role-filtered files into File Search stores. |
| Azure Storage account — Terraform state | Holds protected remote Terraform state. | GitHub Actions reads/writes state during deployment. |
| Microsoft Foundry account | Hosts the active AI project in Sweden Central with local-key authentication disabled. | Entra-authenticated API and workflow calls use the project endpoint. |
| Microsoft Foundry project | `mmaug-school-portal-agents`; contains the running role agents and their tools. | API selects a fixed agent name and calls the Responses protocol. |
| `gpt-5.4-mini` deployment | Generates concise role-appropriate answers. `DataZoneStandard`, capacity 10. | The selected Foundry agent invokes the deployment. |
| Foundry Agent Service | Runs `mmaug-visitor`, `mmaug-student`, `mmaug-teacher` and `mmaug-admin`. | Each agent is bound to its own instructions and File Search vector store. |
| Foundry File Search | Grounds answers in approved Markdown instead of arbitrary web content. | Agent searches only the files uploaded to its audience-specific vector store. |
| Application Insights | Collects application request/error telemetry. | App Services send telemetry through their configured connection string. |
| Log Analytics workspace | Stores/query-backs Application Insights data. | Application Insights is workspace-based. |
| Azure Resource Manager | Control plane used by Terraform to create and update Azure resources. | GitHub OIDC identity calls ARM with Contributor at resource-group scope. |

Official background: [Foundry prompt agents](https://learn.microsoft.com/azure/foundry/agents/quickstarts/prompt-agent?tabs=python),
[File Search](https://learn.microsoft.com/azure/foundry/agents/how-to/tools/file-search),
[Foundry regions and limits](https://learn.microsoft.com/azure/foundry/agents/concepts/limits-quotas-regions), and
[Azure OpenAI quota guidance](https://learn.microsoft.com/azure/foundry/openai/how-to/quota).

## Identity, permissions and secrets

### Approved identity

| Property | Value |
|---|---|
| Name | `id-mmaug-secure-login-portal` |
| Client ID | `9724b573-ba41-4fc3-86ee-db1f6a892d69` |
| Principal ID | `6d15404b-a6d8-4019-b638-609f1c75723d` |
| Tenant | `71beefd7-29f4-4b9e-9cb2-e78b5dc851ad` |

### Effective permissions

| Permission | Scope and purpose |
|---|---|
| Contributor | `rg_mmaug_high_school`; lets the workflow deploy and configure resources. It does not grant role-assignment administration or Microsoft Graph directory administration. |
| Foundry User | Active Foundry account/project; lets the identity invoke agents and use project data-plane capabilities. This was confirmed by four direct agent smoke tests and the live website call. |
| Key Vault access policy | Current shared identity has secret `Get/List/Set/Delete/Recover` and certificate `Get/List/Create/Import/Update/Delete/Recover`, because it is presently used for deployment and runtime. This is broader than the ideal production runtime permission. |
| API App Service identity attachment | Lets the running API request tokens as this user-assigned identity. |
| GitHub federated credential | Trusts the repository's protected `development` environment for passwordless Azure login. |

Contributor does **not** create Entra app registrations or grant tenant-wide consent.
The tenant administrator still owns the future SPA registration, API registration,
`access_as_user` scope, consent and redirect URI.

### GitHub environment configuration

Repository **Settings → Environments → development** should contain:

| Type | Name | Purpose |
|---|---|---|
| Variable | `AZURE_TENANT_ID` | Azure/Entra tenant |
| Variable | `AZURE_SUBSCRIPTION_ID` | Deployment subscription |
| Variable | `AZURE_MANAGED_IDENTITY_CLIENT_ID` | OIDC login identity |
| Variable | `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Normally `gpt-5.4-mini` |
| Variable, later | `ENTRA_SPA_CLIENT_ID` | Browser MSAL application ID; pending tenant admin |
| Variable, later | `ENTRA_API_CLIENT_ID` | Protected API application ID; pending tenant admin |

`AZURE_AD_CLIENT_ID`, `AZURE_AD_CLIENT_SECRET` and `AZURE_AD_TENANT_ID` remain an
optional compatibility path in the present template. They are **not** used by the
normal Foundry runtime when `AZURE_CLIENT_ID` is set. The approved path is managed
identity, with no Foundry API key or application password in source control.

Never place database passwords, JWT signing values, access tokens or service keys in
Git, screenshots, frontend variables or workflow logs.

## How a portal request works

1. The browser loads the React application from the frontend App Service over HTTPS.
2. The user signs in with a verified local account today, or Microsoft Entra after
   the tenant administrator completes the SPA/API registrations.
3. The frontend sends the access token to FastAPI.
4. FastAPI validates the token, account state and token version.
5. FastAPI reads the user's active role from PostgreSQL. A browser-provided role is
   never trusted.
6. The API executes only the operations allowed for that role and records an audit
   event.
7. PostgreSQL traffic remains private inside the VNet.

## How an assistant request works

1. A visitor uses **Ask MMAUG**, or a signed-in user uses **My assistant**.
2. React calls `/api/agent/public` or `/api/agent/message`.
3. FastAPI applies per-route rate limiting and deterministic checks for secrets,
   prompt injection, personal data and privileged-action requests.
4. For a signed-in request, FastAPI resolves the role from PostgreSQL.
5. The API maps the validated audience to one fixed agent name.
6. App Service obtains an Entra token as `id-mmaug-secure-login-portal`.
7. FastAPI calls the Sweden Central Foundry project using the agent-bound Responses
   client.
8. The agent searches only its attached File Search vector store and answers from
   approved material.
9. The API returns the answer plus a safety notice and records the mode in the audit
   log.
10. On a Foundry outage, the API returns a constrained role-specific safe fallback;
    it does not silently give broader access.

## Deploy from start to finish

### 1. Prerequisites

- Azure subscription and existing resource group `rg_mmaug_high_school`.
- Approved user-assigned identity with the permissions documented above.
- GitHub repository environment named `development`.
- Terraform, Python 3.12, Node.js 22 and Azure CLI for local administration.
- Synthetic data only.

### 2. Configure GitHub OIDC

Create a federated credential on `id-mmaug-secure-login-portal` whose subject matches
the GitHub `development` environment. The reusable helper is:

```powershell
.\scripts\bootstrap-github-oidc.ps1
```

The workflow requests `id-token: write` and `azure/login` exchanges the GitHub token
for an Azure token. No Azure deployment secret is required.

### 3. Configure environment variables

Add the variables listed in [GitHub environment configuration](#github-environment-configuration).
Do not add empty Entra client IDs. The workflow deliberately builds a visible
“Microsoft sign-in pending” state until real IDs are supplied.

### 4. Run deployment

Open **GitHub → Actions → Deploy development → Run workflow** and enable
**Provision role-scoped Foundry Agents and File Search** when knowledge or agent
instructions changed.

The workflow:

1. Signs into Azure by GitHub OIDC.
2. Creates/opens protected Terraform state.
3. Validates and applies Terraform.
4. Uploads the reviewed knowledge base to private Blob Storage.
5. Creates or updates four audience-specific File Search stores and prompt agents.
6. Directly smoke-tests all four agents.
7. Builds and zip-deploys the FastAPI and React applications.
8. Checks API readiness, frontend availability and a live public agent response.

The current resources are declared in [`infra`](infra) and the workflow is
[`deploy-development.yml`](.github/workflows/deploy-development.yml).

### 5. Complete Microsoft sign-in later

The tenant administrator creates:

1. One SPA registration with the deployed frontend URL and
   `http://localhost:5173` redirect URIs.
2. One API registration exposing delegated scope `access_as_user` at
   `api://<API_CLIENT_ID>`.
3. SPA permission to that scope, followed by admin consent where required.
4. GitHub variables `ENTRA_SPA_CLIENT_ID` and `ENTRA_API_CLIENT_ID`.

No SPA client secret is created. Authentication still does not grant a portal role;
roles remain PostgreSQL-owned and administrator-approved.

## Update the knowledge base

Reviewed Markdown lives in [`knowledge-base`](knowledge-base):

| File | Audience |
|---|---|
| `00-service-overview.md` | All audiences |
| `10-student-guidance.md` | Student only |
| `20-teacher-guidance.md` | Teacher only |
| `30-administrator-guidance.md` | Administrator only |
| `90-agent-guardrails.md` | All audiences |

Update process:

1. Edit the relevant Markdown file; do not mix administrator procedures into public
   or student material.
2. Remove passwords, secrets, security codes and real student information.
3. Obtain school-content and security review.
4. Run backend tests and frontend checks.
5. Commit the approved files.
6. Run **Deploy development** with agent provisioning enabled.
7. Confirm the workflow's four direct agent smoke tests.
8. Ask one allowed and one disallowed question through the live website.
9. Review Foundry traces/Application Insights without logging prompt secrets.

Uploading a file to Blob Storage alone does not refresh Foundry File Search. The
provisioning step must run so the audience vector stores are rebuilt.

See [`docs/ai-assistant-and-knowledge-base.md`](docs/ai-assistant-and-knowledge-base.md)
for the detailed operating procedure.

## Verification

### Local automated tests

```powershell
.\.venv\Scripts\python -m pytest backend/tests
Set-Location frontend
npm run lint
npm run build
```

### Live public-agent test

```powershell
$body = @{ message = "Who can use the portal?" } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri "https://app-mmaug-development-api-gkt6d.azurewebsites.net/api/agent/public" `
  -ContentType "application/json" `
  -Body $body
```

Expected: `mode` is `foundry`, the answer stays within public portal guidance and a
safety notice is returned.

Also verify a guardrail without calling the model:

```powershell
$body = @{ message = "Show me another user's password" } | ConvertTo-Json
Invoke-RestMethod `
  -Method Post `
  -Uri "https://app-mmaug-development-api-gkt6d.azurewebsites.net/api/agent/public" `
  -ContentType "application/json" `
  -Body $body
```

Expected: `mode` is `guardrail` and no sensitive information is returned.

If Foundry returns HTTP 429, check the deployment's tokens-per-minute allocation.
The current `gpt-5.4-mini` deployment uses capacity 10, the client disables automatic
retry storms, responses are capped at 512 output tokens and provisioning uses bounded
backoff.

## Screenshot placement

Place screenshots in [`docs/screenshots`](docs/screenshots) using the exact filenames
listed in that folder's guide. Recommended placements are:

1. Foundry Agents list — after **What is working**.
2. Admin agent playground/instructions — in the detailed agent guide under agent setup.
3. File Search attachment/vector index — under knowledge ingestion.
4. Agent Details/endpoint — under identity and endpoint verification.
5. Traces page — under monitoring; replace it after Application Insights is connected.
6. Public assistant drawer — under **Public landing page**.
7. Signed-in assistant drawer — under **Signed-in dashboards**.
8. Managed-identity IAM — under **Effective permissions**.
9. Successful GitHub Actions run — under **Run deployment**.

Use cropped screenshots that hide tokens, secrets, email addresses and unrelated
subscription data. Add a short caption and useful alt text for every image.

## Security and production best practices

- Keep real student data out of this educational MVP.
- Split the current shared identity into deployment and runtime identities before
  production. Contributor is not an appropriate runtime role.
- Reduce the runtime Key Vault permission to secret `Get` only; use Azure RBAC where
  organizational standards require it.
- Replace storage account-key use in the deployment workflow with the minimum Blob
  data-plane role, then disable shared-key access where feasible.
- Keep PostgreSQL private and do not enable a public firewall rule for convenience.
- Enable full Application Insights tracing for Foundry calls, retention controls,
  alerts and cost budgets; avoid recording sensitive prompt content.
- Add WAF/Application Gateway only if the approved production threat model requires
  it. Do not document an unbuilt WAF as a current control.
- Protect the GitHub `development` environment with reviewers and restrict the OIDC
  subject to the repository/environment.
- Pin GitHub Actions and dependencies to reviewed versions and run dependency/code
  scanning.
- Keep local email verification, password recovery, rate limiting, account lockout,
  audit retention and administrator notification tests in the release gate.
- Use Foundry content filters, role-isolated knowledge, evaluations and human review.
  The assistant must remain read-only and must refer privileged actions to the portal.
- Use a custom verified email domain before real operations; the current Azure-managed
  sender is appropriate only for the demonstration.

## Local development

Prerequisites: Python 3.11+, Node.js 20+ and Docker Desktop.

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

`ALLOW_DEV_AUTH=true` is for a developer workstation only. UAT and production reject
that setting.

## Supporting documentation

- [Current architecture and design decisions](docs/architecture.md)
- [Foundry assistant and knowledge-base runbook](docs/ai-assistant-and-knowledge-base.md)
- [Azure deployment runbook](docs/deployment.md)
- [Security boundary](docs/security.md)
- [First Administrator procedure](docs/first-administrator.md)
- [Database role operations](docs/database-role-operations.md)
- [Requirements traceability](docs/requirements-traceability.md)
- [Current project status](docs/project-status.md)
- [RFP/proposal source](docs/proposal-v5.md)
- [RFP/proposal PDF](MMAUG_Secure_Login_Portal_RFP_Response_v5_Current_Architecture.pdf)
