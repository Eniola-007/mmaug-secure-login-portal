# Project status — 8 November 2026

## Completed

- Target tenant, subscription, resource group, and North Europe region verified.
- Runtime user-assigned identity created and verified.
- Separate GitHub deployment identity created with no roles or federation yet.
- React/TypeScript portal and FastAPI API implemented.
- Eight synthetic accounts, role dashboards, admin controls, audit events, and recovery route implemented.
- Server-side JWT, scope, role, active-account, and object-level checks implemented.
- Alembic initial migration and local PostgreSQL development configuration added.
- Terraform plan validated against the live Azure subscription: 17 resources to add,
  zero changes, zero deletions after hardening.
- GitHub Actions CI and OIDC deployment workflows added.
- Nine API tests pass with 88% coverage; frontend lint/build pass; npm audit reports zero vulnerabilities.
- Local smoke test passed for migration, readiness, eight-user seed, role dashboard, and HTTP 401 denial.

## External gates

1. **Microsoft Entra permission:** the signed-in account cannot list app registrations
   (`Insufficient privileges`). A tenant administrator must create or delegate access
   to the SPA and API registrations.
2. **Azure RBAC:** no effective role assignment is visible for the signed-in account.
   An Owner/RBAC administrator must authorize the deployment identity and the two
   narrowly scoped Key Vault role assignments.
3. **GitHub coordinates:** exact owner, repository, and environment are required before
   creating the federated credential or publishing the repository.
4. **Cost approval:** the development plan includes a continuously billed B1 App
   Service Plan and B1ms PostgreSQL server. Terraform apply is intentionally paused.
5. **Foundry:** project/model region, quota, permitted agent tools, and budget are not
   yet approved. The API currently returns a constrained role-specific safe demo.
