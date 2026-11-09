# Requirements traceability

| RFP requirement | Implementation | Validation |
|---|---|---|
| Student, teacher, administrator | Database role enum and role-aware UI/API | Role dashboard test |
| Secure sign-in/out | Microsoft identity platform OIDC authorization code + PKCE | Integration test |
| Broad account support | `common` authority for work, school, guest, and personal Microsoft accounts | Cross-account sign-in test |
| Deny-by-default enrollment | Composite tenant/object ID lookup in PostgreSQL | Unenrolled-account 403 test |
| Recovery | Entra password reset delegation | Recovery journey demo |
| Protected API | JWT validation, scope, active status, server-side RBAC | 401/403 tests |
| Account administration | Admin-only list, activation, deactivation, role update | Admin API test |
| Audit events | Append-only event records for sessions and access changes | Audit API test |
| No plaintext passwords | Entra authentication; PostgreSQL bootstrap secret in Key Vault | Config review |
| Five students, two teachers, one admin | Synthetic seed dataset | Seed count/demo |
| CI/CD | GitHub Actions build, test, scan, Terraform, deploy, health check | Workflow run |
| Secretless Azure deployment | GitHub OIDC to dedicated UAMI | OIDC login evidence |
| Separate environments | GitHub environments and Terraform environment variable | Dev/UAT/prod plans |
| Monitoring | Workspace-based Application Insights | Azure telemetry query |
| Private database | VNet delegated PostgreSQL with public access disabled | Terraform plan |
| 1,500 accounts | Stateless API, indexed users, managed database | Load-test record |
| Three agent experiences | Server-side role-selected endpoint; Foundry IDs by role | Isolation tests |
