# Deployment runbook

## 1. Bootstrap facts

- Tenant: `71beefd7-29f4-4b9e-9cb2-e78b5dc851ad`
- Subscription: `9a2ab22e-5269-4da3-a16a-eeed2b0c09aa`
- Resource group: `rg_mmaug_high_school`
- Region: `northeurope`
- Runtime UAMI: `id-mmaug-secure-login-portal`
- Runtime client ID: `9724b573-ba41-4fc3-86ee-db1f6a892d69`
- Deployment UAMI: `id-mmaug-github-deploy`
- Deployment client ID: `5dcac9f2-d372-456b-a622-f395fc57a1c3`
- Deployment principal ID: `80e66122-a06c-4c46-a778-9e1002320189`

## 2. Create Microsoft Entra registrations

Create one SPA registration and one API registration. On the API, expose delegated
scope `access_as_user` with Application ID URI `api://<API_CLIENT_ID>`. Add that scope
to the SPA and grant consent. Configure SPA redirect URIs for `http://localhost:5173`
and the deployed frontend HTTPS URL. Do not create a client secret.

Map the eight synthetic users' Entra object IDs into the database before an Entra
sign-in demonstration. The seed object IDs are local placeholders only.

## 3. Configure GitHub OIDC

After the GitHub owner and repository are known:

```powershell
.\scripts\bootstrap-github-oidc.ps1 `
  -GitHubOwner '<OWNER>' `
  -GitHubRepository '<REPOSITORY>' `
  -Environment development
```

An Owner, User Access Administrator, or Role Based Access Control Administrator must
grant the deployment identity the minimum approved role at the resource-group scope.
Contributor can deploy resources but cannot create role assignments. Prefer a custom
role that omits RBAC writes for steady-state deployment.

The initial Terraform apply creates narrowly scoped Key Vault data-plane roles for the
runtime and deployment principals. The authorized owner must therefore grant temporary
role-assignment authority for bootstrap and review the plan before apply. Remove that
authority after bootstrap if steady-state deployments do not need to change RBAC.

Create GitHub environment `development`, restrict its deployment branches, and add:

- Variables: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`,
  `ENTRA_API_CLIENT_ID`, `ENTRA_SPA_CLIENT_ID`, `API_BASE_URL`
- Secret: `POSTGRES_ADMIN_PASSWORD`

The Azure values are identifiers, not credentials. Never add `AZURE_CLIENT_SECRET` or
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

The default development plan creates paid App Service, PostgreSQL, Log Analytics,
Application Insights, Key Vault, and networking resources. Do not apply without a
budget/SKU decision.

## 5. Deploy and verify

Run the `Deploy development` workflow. Record the workflow URL and verify:

1. `/health/ready` returns HTTP 200.
2. A valid Entra user can sign in and sign out.
3. An invalid or unenrolled user is denied.
4. Each role receives only its dashboard.
5. A student cannot fetch another user's profile.
6. Admin activation and role changes appear in audit activity.
7. Recovery redirects to the tenant-approved Entra journey.
8. The repository contains no client secret or publish profile.
