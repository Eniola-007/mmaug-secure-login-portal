# Project status — 10 November 2026

## Completed in source

- Target tenant, subscription, resource group, North Europe region, and the single
  approved user-assigned managed identity verified.
- React/TypeScript portal and FastAPI API implemented with the supplied MMAUG seal.
- Public presentation-led landing page, Microsoft/email account dialog, and polished
  Student, Teacher, and Administrator dashboards implemented and responsively reviewed.
- Local account registration and sign-in implemented with Argon2id, short-lived API
  tokens, Key Vault signing material, pending approval, and audited database role control.
- Sign-in architecture expanded to Microsoft work, school, guest, and personal accounts.
- Multitenant token validation binds the `tid` claim to the v2 issuer and signing key.
- Database identity changed from object ID alone to composite tenant ID plus object ID.
- Unenrolled users receive clear feedback and a safe enrollment reference.
- Controlled, idempotent database enrollment command added.
- Managed-identity GitHub workflow deploys infrastructure and application packages and
  reports the direct frontend/API App Service URLs for administrator handoff.
- The approved identity now trusts the exact GitHub `development` environment subject.
- The obsolete `id-mmaug-github-deploy` identity was permanently deleted; Azure now has
  only the approved `id-mmaug-secure-login-portal` identity in this resource group.
- PostgreSQL B1ms is approved for the development environment.
- `mmaug-secure-portal.northeurope.cloudapp.azure.com` is reserved on Standard static
  Public IP `68.219.97.185` for the gateway.
- GitHub OIDC login with the single managed identity is verified using the repository-ID
  subject. The obsolete name-based federated credential was removed.
- Terraform includes the approved Linux App Service Plan and an HTTPS Application
  Gateway WAF_v2 with OWASP 3.2 Prevention mode and `/api/*` path routing.
- Eight synthetic accounts, role dashboards, admin controls, audit events, recovery,
  server-side RBAC, object-level checks, migrations, Terraform, CI, and OIDC deployment
  remain implemented.
- Curated student, teacher, administrator, service-overview, and guardrail knowledge files
  are implemented for publication to a private Azure Storage container.
- Dashboards now include role-specific service cards, suggested assistant questions, and
  a server-side guardrail that always derives the role from PostgreSQL.
- The public landing page now includes a separately grounded Visitor assistant limited to
  portal, registration, verification, recovery, approval, and support navigation. It is
  rate-limited and cannot access role guidance or personal school information.
- A controlled first-Administrator enrollment command and Azure App Service SSH runbook
  are implemented; there is no public self-promotion path.
- Microsoft documentation confirms `gpt-5.4-mini` model version `2026-03-17`; the
  deployment name is parameterized for the Foundry administrator handoff.
- Development workflow run `42759323240` completed successfully from commit `382309c`.
- Frontend `https://app-mmaug-development-web-gkt6d.azurewebsites.net` returns HTTP 200
  with the updated role dashboard and assistant interface.
- API liveness and PostgreSQL-backed readiness both return HTTP 200 at
  `https://app-mmaug-development-api-gkt6d.azurewebsites.net`.
- The private `stmmaugkbgkt6d/knowledge-base` container contains the five reviewed
  knowledge and guardrail files.
- The approved Foundry service-principal credential is configured through a resolved Key
  Vault reference. Terraform now creates the Foundry project/model and waits for project
  readiness before creating it, avoiding the transient Azure 409 observed in workflow run
  `42895283734`.
- Workflow run `42941949396` completed successfully from commit `655b2aa`, including
  Terraform apply and provisioning the Visitor, Student, Teacher, and Administrator
  agents. Live agent requests safely fall back until an Owner or User Access Administrator
  grants `id-mmaug-secure-login-portal` **Foundry User**; Contributor cannot assign it.

## Live completion gates

1. Deploy and verify the new public landing page and synthetic-data local account flow.
2. Provide the deployed Web App URL to the Entra administrator, receive the created
   SPA/API client IDs, configure GitHub variables, and
   rerun deployment to activate MSAL.
3. Obtain a trusted TLS certificate, enable Application Gateway WAF_v2, and add the final
   gateway URL to the SPA redirects.
4. Enroll eight synthetic accounts with their real tenant and object IDs.
5. Complete the sign-in, role-isolation, WAF, audit, recovery, and monitoring demonstration.
6. Grant the managed identity and provisioning service principal **Foundry User**, rerun
   deployment, and verify the Visitor, Student, Teacher, and Administrator file-search
   agents plus guarded fallback behavior.
