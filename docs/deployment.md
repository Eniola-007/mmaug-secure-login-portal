# Deployment runbook

## 1. Bootstrap facts

- Tenant: `71beefd7-29f4-4b9e-9cb2-e78b5dc851ad`
- Subscription: `9a2ab22e-5269-4da3-a16a-eeed2b0c09aa`
- Resource group: `rg_mmaug_high_school`
- Region: `northeurope`
- Runtime UAMI: `id-mmaug-secure-login-portal`
- Approved UAMI client ID: `9724b573-ba41-4fc3-86ee-db1f6a892d69`
- Approved UAMI principal ID: `6d15404b-a6d8-4019-b638-609f1c75723d`
- GitHub OIDC subject: `repo:Eniola-007@78024150/mmaug-secure-login-portal@1450348387:environment:development`
- Proposed Azure DNS name: `mmaug-secure-portal.northeurope.cloudapp.azure.com`
- Reserved Standard static Public IP: `pip-mmaug-secure-portal` (`68.219.97.185`)
- PostgreSQL development SKU: `B_Standard_B1ms` (approved 9 November 2026)

## 2. Bootstrap Microsoft identity applications

Run the `Bootstrap Entra applications` workflow in the GitHub `development`
environment. It authenticates as `id-mmaug-secure-login-portal` through OIDC and idempotently:

- creates multitenant SPA and API application registrations;
- creates both home-tenant Enterprise Applications;
- exposes `api://<API_CLIENT_ID>/access_as_user`;
- grants the SPA delegated access and tenant-wide consent;
- configures `http://localhost:5173`; and
- saves `ENTRA_API_CLIENT_ID` and `ENTRA_SPA_CLIENT_ID` as environment variables.

No client secret is created. The managed identity needs the approved Microsoft Graph
application/service-principal and delegated-permission-grant permissions. Azure
Contributor on the resource group does not provide Microsoft Graph permission.

An Entra Privileged Role Administrator or Global Administrator must run the following
once from an authenticated Azure Cloud Shell or administrator workstation:

```powershell
.\scripts\grant-graph-bootstrap-permissions.ps1
```

The script idempotently assigns `Application.ReadWrite.All` and
`DelegatedPermissionGrant.ReadWrite.All` to the approved identity. Rerun the Entra
bootstrap workflow, verify the applications and consent, and then remove those broad
Graph roles.

After deployment, rerun the same workflow with the deployed frontend HTTPS URL. Then
review or remove broad Graph bootstrap permission from the approved identity.

Map each synthetic or external account's tenant ID and object ID into PostgreSQL before
the sign-in demonstration. The `dev-*` seed IDs remain local placeholders only. From
the backend App Service SSH session, validate and apply an enrollment file:

```powershell
python -m app.enroll_users --file /tmp/mmaug-enrollment.json --dry-run
python -m app.enroll_users --file /tmp/mmaug-enrollment.json
```

Use [enrollment.template.json](enrollment.template.json) as the shape. Do not include
passwords or access tokens. An authenticated but unenrolled user sees the required
`tenant_id:object_id` enrollment reference in the portal.

## 3. Configure GitHub OIDC

After the GitHub owner and repository are known:

```powershell
.\scripts\bootstrap-github-oidc.ps1 `
  -GitHubOwner 'Eniola-007' `
  -GitHubRepository 'mmaug-secure-login-portal' `
  -Environment development
```

Verified working federated subject:
`repo:Eniola-007@78024150/mmaug-secure-login-portal@1450348387:environment:development`.

The identity has Contributor at resource-group scope. Contributor can deploy resources,
including the App Service Plan and Application Gateway, but cannot create Azure role
assignments. It also does not grant Microsoft Graph directory permission.

To honor the approved Contributor-only deployment model, the development Key Vault uses
explicit access policies for the approved identity and, when different, the Terraform
caller. Terraform therefore does not create Azure role assignments. This model lets the
single identity write the database bootstrap value and retrieve the TLS certificate.
Reassess Key Vault RBAC and separation of duties before production.

Create GitHub environment `development`, restrict its deployment branches, and add:

- Variables: `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `ENTRA_API_CLIENT_ID`,
  `ENTRA_SPA_CLIENT_ID`, `API_BASE_URL`, `APPLICATION_GATEWAY_ENABLED`,
  `APPLICATION_GATEWAY_DNS_LABEL`, and optional `APPLICATION_GATEWAY_HOST_NAME`
- Secrets: `POSTGRES_ADMIN_PASSWORD` and `APPLICATION_GATEWAY_CERTIFICATE_SECRET_ID`

The approved managed-identity client ID is fixed in both workflows and is not a secret.
The other Azure identifiers are not credentials. Never add `AZURE_CLIENT_SECRET` or
an App Service publish profile.

## 4. Review cost and deploy infrastructure

Copy `infra/terraform.tfvars.example` to `infra/terraform.tfvars`, set the Entra client
IDs, and provide `TF_VAR_postgres_admin_password` outside source control.

```powershell
terraform -chdir=infra init
terraform -chdir=infra fmt -check
terraform -chdir=infra validate
terraform -chdir=infra plan -out development.tfplan
terraform -chdir=infra apply development.tfplan
```

The approved design creates a Linux App Service Plan shared by the frontend and API and,
after TLS inputs are supplied, an Application Gateway WAF_v2. It also creates paid
PostgreSQL, Log Analytics, Application Insights, Key Vault, and networking resources.
The B1ms PostgreSQL development SKU was approved on 9 November 2026. Review production
capacity and retention separately before promoting beyond development.

## 5. Enable Application Gateway WAF_v2

Before setting `APPLICATION_GATEWAY_ENABLED=true`:

1. Use the reserved Azure label `mmaug-secure-portal`, producing
   `mmaug-secure-portal.northeurope.cloudapp.azure.com` on `68.219.97.185`, or supply a
   school-owned domain.
2. Import a trusted certificate into Key Vault and record its **versionless secret ID**.
3. Give `id-mmaug-secure-login-portal` read access to that certificate secret.
4. Set the host-name variable and certificate-secret-ID secret in the GitHub
   `development` environment.
5. Apply Terraform. The Azure label is automatically attached to the Public IP; a custom
   domain instead requires an A/alias record. Use the final HTTPS URL as the SPA redirect
   URI and `API_BASE_URL`.

The gateway redirects port 80 to 443, uses OWASP 3.2 rules in Prevention mode, routes
`/api/*` to FastAPI, and sends all other requests to the React App Service.

Managed identity removes the need for an Entra client secret. It does not remove the TLS
certificate requirement: Application Gateway must receive a PFX directly or retrieve a
certificate from Key Vault. Key Vault reference is selected so the certificate is not
embedded in source, Terraform variables, GitHub artifacts, or the application.

Use two Terraform applies: first deploy the Key Vault and core services with the gateway
disabled; then import the issued certificate, set its versionless secret ID, enable the
gateway, and apply again.

## 6. Deploy and verify

Run the `Deploy development` workflow. Record the workflow URL and verify:

1. `/health/ready` returns HTTP 200.
2. An enrolled Microsoft work, school, guest, or personal account can sign in and out.
3. An invalid or unenrolled user is denied.
4. Each role receives only its dashboard.
5. A student cannot fetch another user's profile.
6. Admin activation and role changes appear in audit activity.
7. Recovery redirects to the tenant-approved Entra journey.
8. The repository contains no client secret or publish profile.
