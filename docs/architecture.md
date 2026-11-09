# Solution architecture

## Identity model

The portal accepts Microsoft work, school, guest, and personal accounts through the
Microsoft identity platform `common` authority. An arbitrary email/password provider is
not accepted directly; a non-Microsoft identity must first be invited as a guest or be
connected through Microsoft Entra External ID.

Authentication and authorization remain separate:

- Microsoft verifies the account and issues the access token.
- FastAPI validates the token signature, v2 issuer, audience, lifetime, tenant ID,
  object ID, and delegated `access_as_user` scope.
- PostgreSQL looks up the composite `(entra_tenant_id, entra_object_id)` identity.
- A valid but unenrolled account receives an enrollment reference and no portal data.
- PostgreSQL assigns the application-level student, teacher, or administrator role.
  Portal administrators are not Microsoft Entra tenant administrators.

```mermaid
flowchart LR
    U[Microsoft work, school, guest,<br/>or personal account]
    SPA[React SPA<br/>authorization code + PKCE]
    IDP[Microsoft identity platform<br/>common authority]
    API[FastAPI protected API]
    DB[(Private PostgreSQL<br/>tenant ID + object ID + role)]
    KV[Azure Key Vault]
    MON[Application Insights]

    U --> SPA
    SPA --> IDP
    IDP -->|v2 access token| SPA
    SPA -->|Bearer token: access_as_user| API
    API -->|enrollment and role check| DB
    API -->|managed identity| KV
    API --> MON
    DB -->|enrolled| API
    DB -.->|not enrolled: 403 + reference| SPA
```

## Directory and deployment objects

```mermaid
flowchart TB
    GH[GitHub Actions development environment]
    DEPLOY[id-mmaug-github-deploy<br/>deployment UAMI]
    APIAPP[API application registration]
    APISP[API Enterprise Application]
    SPAAPP[SPA application registration]
    SPASP[SPA Enterprise Application]
    RG[rg_mmaug_high_school]
    RUNTIME[id-mmaug-secure-login-portal<br/>runtime UAMI]

    GH -->|OIDC federation; no client secret| DEPLOY
    DEPLOY -->|Microsoft Graph bootstrap| APIAPP
    DEPLOY -->|Microsoft Graph bootstrap| SPAAPP
    APIAPP --> APISP
    SPAAPP --> SPASP
    DEPLOY -->|Azure Resource Manager| RG
    RG --> RUNTIME
```

Creating an application registration creates an application definition. Creating its
service principal creates the corresponding Enterprise Application in the home tenant.
The deployment UAMI performs this bootstrap from GitHub OIDC. The runtime UAMI is never
used for directory administration.

After the final HTTPS redirect URI and consent are configured, remove broad Microsoft
Graph bootstrap permissions from the deployment identity unless repeatable directory
provisioning is an approved operational requirement.
