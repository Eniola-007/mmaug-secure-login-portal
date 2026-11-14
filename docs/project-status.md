# Project status — 14 November 2026

## Live and verified

- Frontend: `https://app-mmaug-development-web-gkt6d.azurewebsites.net`.
- API: `https://app-mmaug-development-api-gkt6d.azurewebsites.net`.
- GitHub OIDC uses only `id-mmaug-secure-login-portal` for Azure deployment.
- React landing page, local sign-up/sign-in, verification, recovery and role
  dashboards are deployed.
- Administrators can invite, re-invite, approve, activate, deactivate, assign a
  database role and delete another user from **People & access**.
- Students and teachers have a scoped **My activity** view; administrators have the
  full audit view.
- PostgreSQL Flexible Server 16 B1ms is VNet-injected, private and included in API
  readiness checks.
- Azure Communication Services Email sends verification, invitation, recovery and
  administrator-notification messages; the API checks final send operation status.
- Key Vault, Application Insights, Log Analytics and private knowledge storage are
  deployed in North Europe.
- The active Microsoft Foundry account/project is in Sweden Central with
  `gpt-5.4-mini` DataZoneStandard capacity 10.
- Four persistent agents are Running: `mmaug-visitor`, `mmaug-student`,
  `mmaug-teacher` and `mmaug-admin`.
- Each agent has an audience-specific File Search vector store and passed a direct
  Foundry smoke test.
- The UAMI has effective Foundry User and the live App Service public route returned
  `mode: "foundry"` on 14 November 2026.
- The required MMUAG Bootcamp educational-use caveat is visible in the frontend and
  repository documentation.
- The current test suite contains 40 backend tests; frontend lint/build remain release
  checks.

## Current limitations

- Microsoft browser sign-in is waiting for the tenant administrator's SPA/API app
  registrations, `access_as_user` permission/consent and redirect URI.
- The supplied Foundry Traces screen is not yet connected to Application Insights;
  App Service/Application Insights telemetry remains available.
- Direct App Service HTTPS is the current ingress. Application Gateway/WAF and custom
  DNS are not deployed.
- A single UAMI currently shares deployment and runtime duties; split identities and
  least-privilege storage/Key Vault access are production-hardening tasks.

## Pending administrator action

1. Create the Microsoft Entra SPA and API registrations.
2. Configure `api://<API_CLIENT_ID>/access_as_user`, delegated permission and consent.
3. Add `http://localhost:5173` and the exact frontend App Service HTTPS redirect.
4. Provide `ENTRA_SPA_CLIENT_ID` and `ENTRA_API_CLIENT_ID` as GitHub environment
   variables, then redeploy.

Foundry RBAC is no longer pending.

## Data-use boundary

The environment contains synthetic demonstration data only. It is not approved for
real student data or production adoption.
