# Project status — 9 November 2026

## Completed in source

- Target tenant, subscription, resource group, North Europe region, and the single
  approved user-assigned managed identity verified.
- React/TypeScript portal and FastAPI API implemented with the supplied MMAUG seal.
- Sign-in architecture expanded to Microsoft work, school, guest, and personal accounts.
- Multitenant token validation binds the `tid` claim to the v2 issuer and signing key.
- Database identity changed from object ID alone to composite tenant ID plus object ID.
- Unenrolled users receive clear feedback and a safe enrollment reference.
- Controlled, idempotent database enrollment command added.
- Managed-identity GitHub workflow added to create the SPA/API registrations, their
  Enterprise Applications, `access_as_user`, preauthorization, and delegated consent.
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

## Live completion gates

1. An Entra administrator runs `scripts/grant-graph-bootstrap-permissions.ps1`, then the
   `Bootstrap Entra applications` workflow creates and configures the two applications.
2. Obtain a trusted TLS certificate for the final hostname, import it to Key Vault, and
   grant the identity certificate-secret read access.
3. Deploy the approved B1 App Service Plan, B1ms PostgreSQL, and Application Gateway
   WAF_v2, then rerun the Entra bootstrap with the
   final gateway HTTPS URL.
4. Enroll eight synthetic accounts with their real tenant and object IDs.
5. Complete the sign-in, role-isolation, WAF, audit, recovery, and monitoring demonstration.
6. Approve Foundry region, model, quota, tools, and budget before replacing the current
   constrained role-specific assistant demo.
