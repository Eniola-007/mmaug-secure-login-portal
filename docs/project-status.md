# Project status — 12 November 2026

## Live and verified

- Development frontend: `https://app-mmaug-development-web-gkt6d.azurewebsites.net`.
- Development API: `https://app-mmaug-development-api-gkt6d.azurewebsites.net`.
- GitHub OIDC deployment uses only `id-mmaug-secure-login-portal`; deployment run
  `43043200125` succeeded for commit `1a2d442`.
- React landing page, local sign-up/sign-in, email verification, password recovery and
  role dashboards are deployed.
- Administrators can invite, re-invite, approve, activate, deactivate, assign database
  roles and delete another user from **People & access**.
- Students and teachers have a private **My activity** view; administrators retain the
  complete audit view.
- PostgreSQL Flexible Server 16 B1ms is private, VNet injected and ready; the API readiness
  check includes a live database query.
- Azure Communication Services Email is configured through managed identity; recent send
  requests were accepted and final operation status is now checked by the application.
- Key Vault, Application Insights, Log Analytics, private knowledge storage and the legacy
  North Europe Foundry account/project are provisioned.
- The frontend and README display the required MMUAG Bootcamp educational-use caveat.
- CI passes 34 backend tests, backend lint, frontend lint and production build for the
  current account-lifecycle feature set.

## Deployed with a guarded fallback

- Visitor, Student, Teacher and Administrator assistant interfaces and deterministic
  guardrails are live.
- The live public assistant still returns `safe-demo` for ordinary requests; a successful
  Foundry-agent response is not verified.

## Pending administrator actions

1. Create the Microsoft Entra SPA/API registrations, delegated scope, consent and redirect
   URIs, then provide `ENTRA_SPA_CLIENT_ID` and `ENTRA_API_CLIENT_ID` as GitHub environment
   variables. The deployed API client ID is currently the zero UUID.
2. Merge and deploy the Sweden Central Foundry Agent branch with provisioning disabled.
3. Grant **Foundry User** to `id-mmaug-secure-login-portal` on the new Foundry project,
   wait for propagation, then rerun deployment with agent provisioning enabled.
4. Verify the live public assistant returns `mode: "foundry"` and test each authenticated
   role's isolated knowledge boundary.

Direct App Service HTTPS is the current and documented public ingress.

## Data-use boundary

The environment contains synthetic demonstration data only. It is not approved for real
student data or production adoption.
