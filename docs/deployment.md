# Deployment runbook

## 1. Approved deployment identity

- Tenant: `71beefd7-29f4-4b9e-9cb2-e78b5dc851ad`
- Subscription: `9a2ab22e-5269-4da3-a16a-eeed2b0c09aa`
- Resource group: `rg_mmaug_high_school`
- Region: `northeurope`
- UAMI: `id-mmaug-secure-login-portal`
- UAMI client ID: `9724b573-ba41-4fc3-86ee-db1f6a892d69`
- OIDC subject: `repo:Eniola-007@78024150/mmaug-secure-login-portal@1450348387:environment:development`

The identity has Contributor at resource-group scope. It deploys Azure infrastructure and
application packages. It has no Microsoft Graph directory role and does not create app
registrations or tenant-wide consent.

## 2. Stage-one deployment

Run the `Deploy development` GitHub workflow. It:

1. Exchanges GitHub OIDC for the approved managed identity.
2. Creates a private Azure Storage container for encrypted Terraform state.
3. Deploys networking, private PostgreSQL B1ms, Key Vault, monitoring, the shared Linux
   B1 App Service Plan, and separate API/frontend Web Apps.
4. Generates the PostgreSQL bootstrap password inside Terraform; it is not supplied as a
   GitHub secret or committed to source.
5. Builds the frontend in “MSAL pending” mode using zero-UUID placeholders.
6. Deploys both packages, verifies the API and frontend, and writes both HTTPS URLs to
   the GitHub job summary.

Required GitHub `development` variables for stage one:

- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `APPLICATION_GATEWAY_ENABLED=false`

No Azure client secret, publish profile, PostgreSQL password, or Entra app client ID is
required for the first deployment.

## 3. Administrator handoff

Send the workflow's **Frontend URL** to the Entra administrator. The administrator then:

1. Creates one SPA registration and one API registration.
2. Creates or verifies their Enterprise Applications.
3. On the API, exposes delegated scope `access_as_user` with Application ID URI
   `api://<API_CLIENT_ID>`.
4. Adds that scope to the SPA and grants the approved consent.
5. Configures SPA redirect URIs:
   - `http://localhost:5173`
   - the exact direct frontend App Service HTTPS URL
   - later, the final Application Gateway HTTPS URL
6. Creates no client secret.
7. Returns the SPA and API client IDs.

Save the returned identifiers as GitHub `development` variables:

- `ENTRA_SPA_CLIENT_ID`
- `ENTRA_API_CLIENT_ID`

Rerun `Deploy development`. The frontend is rebuilt with MSAL enabled and the API is
configured to validate tokens for the registered API audience.

## 4. Enrollment

Map each synthetic account's real Entra tenant ID and object ID into PostgreSQL before
the sign-in demonstration. The seed object IDs are local placeholders only.

```powershell
python -m app.enroll_users --file /tmp/mmaug-enrollment.json --dry-run
python -m app.enroll_users --file /tmp/mmaug-enrollment.json
```

Use [enrollment.template.json](enrollment.template.json). Never include passwords or
access tokens in the enrollment file.

## 5. Application Gateway WAF_v2

The final hostname is `mmaug-secure-portal.northeurope.cloudapp.azure.com`, reserved on
Standard static Public IP `68.219.97.185`.

After obtaining a trusted certificate:

1. Import it into Key Vault and record its versionless secret ID.
2. Set `APPLICATION_GATEWAY_CERTIFICATE_SECRET_ID` as a protected GitHub secret.
3. Set `APPLICATION_GATEWAY_ENABLED=true`.
4. Rerun the deployment workflow.
5. Add the gateway HTTPS URL to the SPA redirect URIs.

The gateway redirects HTTP to HTTPS, applies OWASP 3.2 rules in Prevention mode, routes
`/api/*` to FastAPI, and routes all other paths to React.

## 6. Acceptance verification

1. `/health/ready` returns HTTP 200.
2. The frontend URL returns HTTP 200 and displays the MMAUG-branded portal.
3. Before handoff, the portal displays “MSAL pending” and cannot initiate invalid login.
4. After handoff, an enrolled Microsoft account can sign in and out.
5. An unenrolled account receives no portal data.
6. Each role receives only its dashboard and permitted objects.
7. Administrative changes create audit events.
8. WAF and Application Insights record the expected telemetry.
9. The repository contains no Azure client secret or publish profile.
