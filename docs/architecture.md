# Current architecture and decisions

**As of:** 14 November 2026<br>
**Scope:** development demonstration using synthetic data only

![Current Microsoft-style Azure architecture](architecture-current.svg)

## 1. Current deployment

The portal uses two Azure regions:

- **North Europe** hosts the React and FastAPI App Services, shared Linux B1 App
  Service Plan, user-assigned managed identity, private PostgreSQL, Key Vault,
  networking, email, storage and monitoring.
- **Sweden Central** hosts the active Microsoft Foundry account, project,
  `gpt-5.4-mini` DataZoneStandard deployment, four prompt agents and audience-isolated
  File Search vector stores.

The resource group is `rg_mmaug_high_school`. The active Foundry account is
`aifoundry-mmaug-development-agents-gkt6d`; the project is
`mmaug-school-portal-agents`. The deleted North Europe Foundry project is not part of
the current architecture.

Direct Azure App Service HTTPS is the current ingress. Application Gateway, WAF and
custom DNS are not deployed. They are therefore excluded from the current-state
diagram and from claimed controls.

## 2. Trust boundaries

### Browser boundary

The frontend renders the user experience but does not decide authorization. It sends
tokens and requested operations to FastAPI. It cannot activate accounts, select a
database role or select a Foundry agent.

### API boundary

FastAPI is the security and orchestration boundary. For protected requests it:

1. validates the token and account/token-version state;
2. reads the active Student, Teacher or Administrator role from PostgreSQL;
3. enforces route authorization and rate limits;
4. applies deterministic assistant guardrails;
5. selects a fixed agent name from the validated audience;
6. records an audit event.

### Data boundary

PostgreSQL is reachable only through the VNet's private route and private DNS. It
stores application profiles, password hashes for local accounts, immutable Entra
identity keys, role assignments, invitation/verification state, audit events and
rate-limit records. Role changes go through authorized application operations so
verification checks and audit events cannot be bypassed.

### AI boundary

The API invokes Foundry with `id-mmaug-secure-login-portal`. Each role has a separate
agent and File Search vector store. Agents have no state-changing school tool. The
model receives neither credentials nor unrestricted database access. If the Foundry
call fails, the API returns a constrained role-specific fallback.

## 3. Role and agent mapping

| Validated audience | API route | Foundry agent | Knowledge |
|---|---|---|---|
| Public visitor | `/api/agent/public` | `mmaug-visitor` | Service overview + guardrails |
| Student | `/api/agent/message` | `mmaug-student` | Overview + student + guardrails |
| Teacher | `/api/agent/message` | `mmaug-teacher` | Overview + teacher + guardrails |
| Administrator | `/api/agent/message` | `mmaug-admin` | Overview + administrator + guardrails |

The PostgreSQL role is authoritative. Neither a token claim supplied by a local
client nor the question text can move a user to a different agent.

## 4. Service communication

| From | To | Protocol/trust | Purpose |
|---|---|---|---|
| Browser | Frontend App Service | HTTPS | Load landing page and dashboards |
| Frontend | API App Service | HTTPS/JSON + token | Authentication and application operations |
| API | PostgreSQL | TLS 5432 through VNet/private DNS | Users, roles, audit and rate-limit state |
| API App Service | Key Vault | App Service reference + UAMI | Resolve DB URL and JWT value |
| API | ACS Email | Azure SDK + Azure identity | Verification, invitations, recovery and alerts |
| API | Foundry project | Entra token + Responses API | Invoke one server-selected role agent |
| Foundry agent | File Search | Agent tool binding | Search only its audience vector store |
| Foundry agent | `gpt-5.4-mini` | Foundry internal model invocation | Generate grounded answer |
| App Services | Application Insights | Connection string/agent | Request and failure telemetry |
| GitHub Actions | Azure Resource Manager | OIDC + Contributor | Terraform and application deployment |
| GitHub Actions | Foundry project | OIDC + Foundry User | Agent/vector-store provisioning and tests |
| GitHub Actions | Blob Storage | Current masked account-key operation | Publish reviewed knowledge source copy |

## 5. Managed identity and permissions

The single approved identity is:

- name: `id-mmaug-secure-login-portal`
- client ID: `9724b573-ba41-4fc3-86ee-db1f6a892d69`
- principal ID: `6d15404b-a6d8-4019-b638-609f1c75723d`

It currently has Contributor on `rg_mmaug_high_school`, Foundry User on the active
Foundry scope and a Key Vault access policy used by both deployment and runtime. The
API App Service has the UAMI attached and `AZURE_CLIENT_ID` selects it explicitly.

Contributor does not grant Entra application-registration permissions, Microsoft
Graph directory permissions or the right to assign Azure roles. The tenant
administrator remains responsible for SPA/API registrations, consent and redirects.

For production, split deployment and runtime identities, reduce the runtime Key Vault
permission to secret `Get`, and replace storage account-key use with the minimum Blob
data-plane role.

## 6. Authentication modes

### Current local account flow

Users can create a local account, verify email, reset a password and wait for an
administrator to approve/activate a database role. Passwords are stored as Argon2id
hashes. Sign-up does not accept an elevated role.

### Pending Microsoft flow

The tenant administrator must provide one SPA and one API registration. The API will
expose `access_as_user`; the SPA will request that delegated scope and use
`common` authority so supported work, school, guest or personal Microsoft accounts
can authenticate. Portal access still requires an approved PostgreSQL record.

## 7. Deployment architecture

GitHub Actions uses an environment-bound federated credential and Azure OIDC. The
workflow applies Terraform, publishes reviewed knowledge, provisions and directly
tests all four agents, deploys API/frontend packages and performs live health and
agent tests. No Azure deployment client secret is required.

Remote Terraform state is kept in a dedicated private Blob container. Database and
JWT values are generated/stored in Key Vault and referenced by App Service rather
than copied into GitHub or browser configuration.

## 8. Verified state and remaining work

Verified on 14 November 2026:

- four persistent role agents are Running;
- each role agent passed a direct Foundry smoke test;
- the UAMI can invoke the Sweden Central project with Foundry User;
- the live App Service public endpoint returned `mode: foundry`;
- input guardrails and safe fallback remain in place;
- PostgreSQL is private and the application health endpoint is ready.

Remaining tenant-admin integration is Microsoft SPA/API registration and consent.
Before production, complete identity separation, storage-key removal, Foundry trace
connection, alerting, data-protection assessment, penetration testing and real-data
governance.

## 9. Key design decisions

1. **Database-owned roles:** authentication proves identity; PostgreSQL controls
   school authorization.
2. **Four isolated agents:** role separation exists in both server routing and
   knowledge retrieval, not only in prompt text.
3. **Managed identity first:** runtime and workflow avoid Foundry API keys.
4. **Private database:** the VNet remains because App Service Plan alone does not make
   PostgreSQL private.
5. **No unbuilt WAF claim:** current diagrams show direct App Service HTTPS only.
6. **Read-only assistant:** human-approved portal workflows make changes; the model
   only explains approved guidance.
