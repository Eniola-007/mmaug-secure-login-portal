# Project status — 10 November 2026

## Completed in source

- Target tenant, subscription, resource group, North Europe region, and the single
  approved user-assigned managed identity verified.
- React/TypeScript portal and FastAPI API implemented with the supplied MMAUG seal.
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
- Microsoft documentation confirms `gpt-5.4-mini` model version `2026-03-17`; the
  deployment name is parameterized for the Foundry administrator handoff.

## Live completion gates

1. Run the infrastructure-first GitHub deployment and provide the returned Web App URL
   to the Entra administrator.
2. Receive the administrator-created SPA/API client IDs, configure GitHub variables, and
   rerun deployment to activate MSAL.
3. Obtain a trusted TLS certificate, enable Application Gateway WAF_v2, and add the final
   gateway URL to the SPA redirects.
4. Enroll eight synthetic accounts with their real tenant and object IDs.
5. Complete the sign-in, role-isolation, WAF, audit, recovery, and monitoring demonstration.
6. Administrator creates the Foundry project/model deployment and three file-search
   agents, then grants the managed identity **Foundry User** and the required Storage data
   role. Configure the project endpoint and role agent names to replace safe fallback.
