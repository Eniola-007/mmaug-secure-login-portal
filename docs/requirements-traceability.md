# Requirements traceability

Status meanings: **Live** is deployed and tested, **Pending** requires an administrator or
acceptance step, and **Planned** is implemented in design/source but not deployed.

| Requirement | Implementation | Status and evidence |
|---|---|---|
| Student, Teacher and Administrator | PostgreSQL role enum, FastAPI dependencies and role dashboards | **Live** — API/UI tests |
| Public landing page | React public site with school branding and educational caveat | **Live** — deployed frontend |
| Local sign-in and recovery | Argon2id, verified email, versioned JWT, one-time recovery | **Live** — authentication tests |
| Microsoft sign-in | SPA authorization code with PKCE; API `access_as_user` validation | **Pending** — client IDs are zero UUID |
| Deny-by-default enrollment | Inactive registration and composite tenant/object lookup | **Live** — negative access tests |
| Account administration | Invite, re-invite, role update, activation, deactivation and deletion | **Live** — admin API tests |
| Activity records | Administrator-wide audit and user-scoped activity | **Live** — access-control tests |
| No plaintext passwords | Argon2id local hashes; secrets in Key Vault | **Live** — code/config review |
| Synthetic demonstration accounts | Seed data and controlled enrollment tooling | **Live for demo** — real student data prohibited |
| CI/CD | GitHub CI plus OIDC Terraform/application/agent deployment | **Live** — infrastructure, four direct agent smoke tests and both application deployments completed in run `43482591262`; its first cold live-agent check timed out, then the same deployed route passed a bounded live retest |
| Secretless Azure deployment | Environment OIDC to the single approved UAMI | **Live** — Azure/GitHub evidence |
| Private database | VNet-injected PostgreSQL, linked private DNS, no public access | **Live** — Azure resource state |
| Email verification and invitations | ACS Email through managed identity; final operation check | **Live** — dependency telemetry and tests |
| Monitoring | Application Insights and Log Analytics | **Live** — workspace and dependency telemetry |
| Role-aware assistant UI | Public and signed-in drawers, server-selected role, deterministic guardrails and safe fallback | **Live** — route tests and deployed UI |
| Foundry model | Sweden Central project and `gpt-5.4-mini` DataZoneStandard capacity 10 | **Live** — four direct agent tests and website `mode: foundry` response |
| Curated agent knowledge | Private Blob source plus four audience-isolated File Search stores | **Live** — agent-specific provisioning and grounded smoke tests |
| Separate environments | GitHub environment and Terraform environment variable | **Development live; UAT/production not deployed** |
| 1,500 accounts | Indexed stateless design | **Pending** — load test not completed |
| Production governance | Privacy, retention, backup/restore, penetration and operations | **Pending** — mandatory before real data |
