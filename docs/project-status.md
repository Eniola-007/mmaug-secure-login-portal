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
- Terraform includes the approved Linux App Service Plan and an HTTPS Application
  Gateway WAF_v2 with OWASP 3.2 Prevention mode and `/api/*` path routing.
- Eight synthetic accounts, role dashboards, admin controls, audit events, recovery,
  server-side RBAC, object-level checks, migrations, Terraform, CI, and OIDC deployment
  remain implemented.

## Live completion gates

1. Run `Bootstrap Entra applications` using `id-mmaug-secure-login-portal` and confirm its
   Microsoft Graph permission is effective.
2. Provide the approved portal DNS host name and a versionless Key Vault TLS certificate
   secret ID, then grant the identity certificate-secret read access.
3. Approve the continuously billed B1ms PostgreSQL resource or select another SKU. The
   App Service Plan and Application Gateway WAF_v2 are already approved.
4. Deploy, point DNS at the gateway public IP, then rerun the Entra bootstrap with the
   final gateway HTTPS URL.
5. Enroll eight synthetic accounts with their real tenant and object IDs.
6. Complete the sign-in, role-isolation, WAF, audit, recovery, and monitoring demonstration.
7. Approve Foundry region, model, quota, tools, and budget before replacing the current
   constrained role-specific assistant demo.
