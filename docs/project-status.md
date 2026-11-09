# Project status — 9 November 2026

## Completed in source

- Target tenant, subscription, resource group, North Europe region, and two user-assigned
  managed identities verified.
- React/TypeScript portal and FastAPI API implemented with the supplied MMAUG seal.
- Sign-in architecture expanded to Microsoft work, school, guest, and personal accounts.
- Multitenant token validation binds the `tid` claim to the v2 issuer and signing key.
- Database identity changed from object ID alone to composite tenant ID plus object ID.
- Unenrolled users receive clear feedback and a safe enrollment reference.
- Controlled, idempotent database enrollment command added.
- Managed-identity GitHub workflow added to create the SPA/API registrations, their
  Enterprise Applications, `access_as_user`, preauthorization, and delegated consent.
- Eight synthetic accounts, role dashboards, admin controls, audit events, recovery,
  server-side RBAC, object-level checks, migrations, Terraform, CI, and OIDC deployment
  remain implemented.

## Live completion gates

1. Run `Bootstrap Entra applications` using `id-mmaug-github-deploy` and confirm its
   Microsoft Graph permission is effective.
2. Approve the continuously billed B1 App Service Plan and B1ms PostgreSQL resources,
   or select lower approved SKUs before Terraform apply.
3. Deploy, then rerun the Entra bootstrap with the generated frontend HTTPS URL.
4. Enroll eight synthetic accounts with their real tenant and object IDs.
5. Complete the sign-in, role-isolation, audit, recovery, and monitoring demonstration.
6. Approve Foundry region, model, quota, tools, and budget before replacing the current
   constrained role-specific assistant demo.
