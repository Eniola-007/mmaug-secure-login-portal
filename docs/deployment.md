# Deployment runbook

Current development state: the frontend and API App Services, private PostgreSQL, email,
monitoring, knowledge storage, and legacy North Europe Foundry resources are deployed.
The Sweden Central Foundry Agent project is a pending branch change and is not live.
Microsoft client IDs and Foundry RBAC remain completion gates.

## 1. Approved deployment identity

- Tenant: `71beefd7-29f4-4b9e-9cb2-e78b5dc851ad`
- Subscription: `9a2ab22e-5269-4da3-a16a-eeed2b0c09aa`
- Resource group: `rg_mmaug_high_school`
- Region: `northeurope`
- UAMI: `id-mmaug-secure-login-portal`
- UAMI client ID: `9724b573-ba41-4fc3-86ee-db1f6a892d69`
- UAMI principal ID: `6d15404b-a6d8-4019-b638-609f1c75723d`
- OIDC subject: `repo:Eniola-007@78024150/mmaug-secure-login-portal@1450348387:environment:development`

The identity has Contributor at resource-group scope. It deploys Azure infrastructure and
application packages. It has no Microsoft Graph directory role and does not create app
registrations or tenant-wide consent. The workflow verifies that its OIDC client ID matches
the API's user-assigned managed identity client ID.

## 2. Stage-one deployment

Run the `Deploy development` GitHub workflow. It:

1. Exchanges GitHub OIDC for the approved managed identity.
2. Creates a private Azure Storage container for encrypted Terraform state.
3. Deploys networking, private PostgreSQL B1ms, Key Vault, monitoring, the shared Linux
   B1 App Service Plan, and separate API/frontend Web Apps.
4. Generates the PostgreSQL bootstrap password inside Terraform; it is not supplied as a
   GitHub secret or committed to source.
5. Builds the frontend in “MSAL pending” mode when the Entra client-ID variables are not
   available. This is the current deployed state.
6. Deploys both packages, verifies the API and frontend, and writes both HTTPS URLs to
   the GitHub job summary.

Required GitHub `development` variables for stage one:

- `AZURE_MANAGED_IDENTITY_CLIENT_ID` (must match the runtime UAMI client ID above)
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`

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

The workflow uploads reviewed Markdown to the private `knowledge-base` Blob container and
masks the storage key immediately. This copy is for deployment/storage; it does not itself
populate Foundry File Search.

The branch Terraform creates a separate Sweden Central Foundry account/project and
`gpt-5.4-mini` deployment while preserving the existing North Europe resources. The first
workflow run must leave **Provision role-scoped Foundry Agents and File Search** unchecked.
After Terraform succeeds, the workflow summary reports the project name and resource ID
and the API managed-identity principal ID.

An authorized Azure administrator must grant **Foundry User** on the new project to
`id-mmaug-secure-login-portal` (principal ID shown in the workflow summary). Open the
project's **Access control (IAM)**, select **Add role assignment**, choose **Foundry User**,
select **Managed identity → User-assigned managed identity**, then choose that identity
from `rg_mmaug_high_school` and confirm the principal ID before assigning. Assign at the
project scope, not the subscription or whole resource group. This role allows the runtime
API to invoke agents and allows the protected GitHub workflow to create and update them.
The workflow fails early unless its OIDC client ID matches the runtime identity.

Role assignment requires **Owner**, **User Access Administrator**, or an equivalent role
assignment permission; Resource Group Contributor alone cannot grant RBAC. Wait for role
propagation, then rerun the workflow with agent provisioning checked. It creates four
agents (visitor, student, teacher, administrator), each with an isolated File Search
store. The deployment smoke test fails unless the public assistant returns
`mode: "foundry"`.

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
- Every new Microsoft signup receives a confirmation email; Microsoft identity ownership
  is already verified by the validated Entra token, so no second verification link is used.
- Active database Administrators receive an email alert when a local user verifies their
  mailbox, a pre-enrolled user completes password setup, or a new Microsoft identity is
  registered. The alert links back to **People & access** for the role decision.
- Administrators can invite a new school member with a Student, Teacher, or Administrator
  database role from **People & access**. The inactive record receives a one-time setup
  email, and **Re-send invite** rotates unused setup or verification links.
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

## 7. Acceptance verification

1. `/health/ready` returns HTTP 200.
2. The frontend URL returns HTTP 200 and displays the MMAUG-branded portal.
3. Before handoff, the portal displays “MSAL pending” and cannot initiate invalid login.
4. After handoff, an enrolled Microsoft account can sign in and out.
5. An unenrolled account receives no portal data.
6. Each role receives only its dashboard and permitted objects.
7. Administrative changes create audit events.
8. Application Insights records expected telemetry.
9. The repository contains no Azure client secret or publish profile.
10. The knowledge container is private and contains only reviewed files.
11. The public assistant returns `mode: "foundry"` and each role agent stays inside its
    server-selected boundary and refuses cross-user data.
12. Local signup requires email verification before administrator activation.
13. Password reset revokes an older local session and public auth endpoints rate-limit.
