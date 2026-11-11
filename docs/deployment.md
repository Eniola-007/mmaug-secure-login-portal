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

These IDs are identifiers, not credentials. Use **Repository → Settings → Environments →
development → Environment variables**, not Environment secrets. Do not create a SPA
client secret. The redirect URL is configured on the SPA registration in Entra, not in
GitHub.

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

For the first authorized portal Administrator, follow the App Service console procedure
in [first-administrator.md](first-administrator.md). This is a database application role,
not an Entra directory role or Azure RBAC role.

For local registrations, approval is in the authenticated portal: **Administrator
dashboard → People & access**. A local user must complete the emailed ownership check
before **Approve & activate** becomes available. The administrator chooses the PostgreSQL
role there; a user cannot approve or promote their own registration.

## 5. Foundry knowledge and role agents

The workflow creates a private `knowledge-base` Blob container and uploads the reviewed
Markdown files from the repository. It obtains a storage key only for that upload, masks
it immediately, and does not store it in GitHub or application settings.

Terraform creates the Foundry resource, `mmaug-school-portal` project, and the approved
`gpt-5.4-mini` version `2026-03-17` deployment. The workflow then attempts to create one
public visitor agent plus three role-scoped agents, each with a separate file-search store
containing only its reviewed Markdown boundary.

The Foundry administrator must:

1. open Foundry account `aifoundry-mmaug-development-gkt6d`, then project
   `mmaug-school-portal`, and select **Access control (IAM)**;
2. add **Foundry User** (role definition `53ca6127-db72-4b80-b1b0-d745d6d5456d`);
3. choose **Managed identity → User-assigned managed identity** and select
   `id-mmaug-secure-login-portal`;
4. confirm principal ID `6d15404b-a6d8-4019-b638-609f1c75723d`, then select
   **Review + assign** twice;
5. wait several minutes for Azure RBAC propagation and rerun **Deploy development**; and
6. verify grounded answers, role isolation, refusals, fallback, and audit metadata.

The least-privilege assignment scope is:

```text
/subscriptions/9a2ab22e-5269-4da3-a16a-eeed2b0c09aa/resourceGroups/rg_mmaug_high_school/providers/Microsoft.CognitiveServices/accounts/aifoundry-mmaug-development-gkt6d/projects/mmaug-school-portal
```

The same approved managed identity is used by the API at runtime and by GitHub OIDC during
agent provisioning. The provisioning step deliberately uses the Azure CLI session created
by `azure/login`; it does not require an application password.

`Contributor` is not sufficient for agent inference. The runtime managed identity must
also have **Foundry User** on the Foundry account or project. Both the API and protected
provisioning workflow use that managed identity; neither needs a Foundry client secret.

Creating those role assignments requires **Owner**, **User Access Administrator**, or an
equivalent role-assignment permission. Resource-group Contributor alone cannot grant RBAC.

Do not put a Foundry API key or application password in the repository. Microsoft Entra
managed identity is the runtime and deployment authentication mechanism.

## 6. Local-account email and recovery

Terraform creates Azure Communication Services Email with an Azure-managed sender domain.
The API authenticates to it with `id-mmaug-secure-login-portal`; no email connection string
is stored in GitHub or sent to the browser.

- Verification and password-reset tokens are random, single-use, short-lived, and stored
  only as SHA-256 digests in PostgreSQL.
- Every new local signup receives an email-verification message. A pre-enrolled account
  without a local password receives a one-time password-setup message that also verifies
  mailbox ownership.
- Administrators cannot assign a different database role or activate a local account until
  email verification is complete.
- Password reset increments the account authentication version, revoking older local JWTs.
- Registration, sign-in, verification, resend, and recovery limits persist in PostgreSQL
  and return HTTP 429 with `Retry-After` when exceeded.
- Recovery responses do not reveal whether an email is registered.

Before real student data is accepted, verify outbound delivery and suppression behavior,
complete a data-protection review, and replace the limited Azure-managed sender with a
verified school domain if production volume or branding requires it.

The API starts its idempotent Alembic migration in a background worker so App Service can
answer platform warm-up probes immediately. `/health/ready` remains unavailable until the
migration and a live PostgreSQL query both succeed.

## 7. Application Gateway WAF_v2

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

## 8. Acceptance verification

1. `/health/ready` returns HTTP 200.
2. The frontend URL returns HTTP 200 and displays the MMAUG-branded portal.
3. Before handoff, the portal displays “MSAL pending” and cannot initiate invalid login.
4. After handoff, an enrolled Microsoft account can sign in and out.
5. An unenrolled account receives no portal data.
6. Each role receives only its dashboard and permitted objects.
7. Administrative changes create audit events.
8. WAF and Application Insights record the expected telemetry.
9. The repository contains no Azure client secret or publish profile.
10. The knowledge container is private and contains only reviewed files.
11. Each role agent stays inside its server-selected boundary and refuses cross-user data.
12. Local signup requires email verification before administrator activation.
13. Password reset revokes an older local session and public auth endpoints rate-limit.
