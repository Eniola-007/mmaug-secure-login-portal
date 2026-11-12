# Solution architecture

> **Educational-use caveat:** The MMAUG Secure Login Portal was built for the Malta
> Microsoft AI User Group (MMUAG) AI & DevOps Fundamentals Bootcamp 2026. It is a
> demo/educational solution and must not be adopted as a production-ready system.

## Current deployed architecture

![Microsoft-style current working Azure architecture](architecture-current.svg)

The development environment is deployed in North Europe in
`rg_mmaug_high_school`. The public entry point currently used by visitors is the direct
frontend App Service URL:

`https://app-mmaug-development-web-gkt6d.azurewebsites.net`

The deployed components are:

- one Linux B1 App Service Plan with separate React frontend and FastAPI API Web Apps;
- one approved user-assigned identity, `id-mmaug-secure-login-portal`, used by GitHub
  OIDC for deployment and attached to the API for approved runtime access;
- PostgreSQL Flexible Server 16, B1ms, in the delegated `snet-postgresql` subnet with
  public access disabled and private DNS linked to the VNet;
- API App Service VNet integration through `snet-appservice`;
- Key Vault references for the database URL and local-token signing value;
- Azure Communication Services Email for invitations, verification, recovery and
  administrator alerts;
- workspace-based Application Insights and Log Analytics;
- a private knowledge-base Storage account and container; and
- the legacy North Europe Microsoft Foundry project and model deployment, currently
  outside the active runtime path.

The current public ingress is the HTTPS endpoint supplied by Azure App Service. The
current-state diagram contains only components and paths that are working now.

## Request and authorization path

1. Visitors load the public React application over the frontend App Service HTTPS URL.
2. The browser calls the FastAPI App Service for registration, sign-in, dashboards,
   account administration and assistant messages.
3. FastAPI authenticates the request, then reads `is_active` and `role` from PostgreSQL.
4. PostgreSQL—not the browser, token or assistant—selects Student, Teacher or
   Administrator authorization.
5. Administrative changes, user deletion, invitations and significant authentication
   events are recorded in the audit table.
6. The API uses VNet integration and private DNS to reach PostgreSQL; the database has no
   public endpoint.

Authorized operators can inspect the database read-only through the API App Service SSH
console, which is already on the private network. Direct public database access is not
enabled for administration.

## Authentication state

Local email/password authentication is live for synthetic demonstration accounts:

- passwords are hashed with Argon2id;
- registrations start inactive and cannot choose a role;
- email verification is required before local activation or role change;
- one-time verification, invitation and recovery values are stored only as digests;
- password reset revokes previous local sessions; and
- public authentication endpoints use PostgreSQL-backed rate limits.

Microsoft authentication is implemented in code but not active in the deployed build.
The API client ID is still the zero UUID. A tenant administrator must create the SPA/API
registrations, delegated `access_as_user` scope, consent and redirect URI, then provide
the two non-secret client IDs as GitHub environment variables. No SPA or API client
secret is required.

After activation, FastAPI validates signature, issuer, audience, lifetime, tenant ID,
object ID and delegated scope before PostgreSQL resolves the immutable
`(entra_tenant_id, entra_object_id)` mapping.

## Email path

The API authenticates to Azure Communication Services with the user-assigned managed
identity; no connection string is stored in GitHub or exposed to the browser. The API
waits for the final ACS operation result before reporting an invitation as sent.

The Azure-managed sender is appropriate only for this demonstration. Delivery, junk
classification and suppression behavior must be validated before any broader use, and a
verified school-owned domain should be considered for a future operational service.

## Assistant and knowledge boundary

The public site and each role dashboard have an assistant experience. FastAPI always
selects the signed-in assistant from the PostgreSQL role. Deterministic pre-model
guardrails refuse prompt override, credential, cross-user-data and privileged-action
requests. Agents receive no state-changing tools.

The live API has not yet been verified against a Foundry Agent; ordinary questions still
return the safe demo/fallback. A pending branch change adds a separate Sweden Central
Foundry Agent Service project with four agents and isolated File Search stores while
keeping the web app and PostgreSQL in North Europe. The migration requires a successful
deployment, **Foundry User** on the new project for the API's user-assigned identity, and
grounding/isolation tests before the website can be described as agent-backed.

## Deployment and identity boundary

GitHub Actions uses environment-bound workload identity federation to obtain an Azure
token for `id-mmaug-secure-login-portal`. Terraform and the zip-deployment steps use that
token; no Azure client secret or App Service publish profile is committed.

The managed identity has no Microsoft Graph directory permission. Creating Entra app
registrations, granting consent and assigning Azure roles remain administrator actions.
The repository workflow cannot grant itself additional RBAC.

## Completion gates outside the working diagram

These items are documented here rather than shown as active architecture components:

1. Create and configure the Microsoft Entra SPA/API registrations and redeploy with their
   client IDs.
2. Merge and deploy the Sweden Central agent branch, grant the API managed identity
   **Foundry User** on the new Foundry project, allow propagation, provision agents, and
   complete grounding/isolation tests.
3. Complete privacy, retention, backup/restore, penetration, accessibility, incident
   response and operational-ownership reviews before considering real student data.
