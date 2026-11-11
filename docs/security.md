# Security boundary

## Identity and authorization

- The Microsoft identity platform performs authentication, MFA, recovery, and token issuance.
- The `common` authority accepts Microsoft work, school, guest, and personal accounts.
- The SPA requests an access token for the API using authorization code + PKCE.
- People without Microsoft accounts may create a local portal account. Passwords are
  hashed with Argon2id and are never returned or logged.
- Local access tokens are short-lived, signed server-side with a random value held in Key
  Vault, and stored only in browser session storage.
- FastAPI validates signature, tenant-bound v2 issuer, signing-key issuer, audience,
  expiry, tenant ID, object ID, and `access_as_user` scope.
- Tenant ID and object ID form the authorization lookup key because object IDs are only
  unique inside a tenant.
- New Microsoft and local registrations receive no portal data until an administrator
  verifies, assigns, and activates the PostgreSQL role.
- Self-registration rejects role input and defaults to an inactive Student record, so a
  visitor cannot self-assign Teacher or Administrator.
- Portal role and active status are loaded server-side from PostgreSQL for every request.
- Students and teachers can read only their own profile. Only administrators can list or change users.
- Administrative changes are deterministic API operations and create an audit event.
- The role-specific AI endpoint selects the role on the server. An LLM is never an authorization layer.
- The API rejects prompt overrides, secret requests, cross-user records, and privileged
  action requests before calling Foundry.
- Foundry is configured to use the App Service managed identity and reviewed role-scoped
  knowledge. The identity has effective **Foundry User** and **Azure AI Developer** on the
  Foundry account. The model receives no credentials, raw database access or
  state-changing tools; requests fail safely into a constrained fallback during outages.
- When the administrator-approved Foundry service principal is enabled, its client secret
  is a write-only Terraform input stored in Key Vault; the Web App setting is a Key Vault
  reference and the GitHub workflow continues to deploy through managed-identity OIDC.

## Managed identities

`id-mmaug-secure-login-portal` is the only approved managed identity. Its GitHub
federated credential trusts the exact repository and `development` environment subject.
It deploys infrastructure and code and is attached to the API.
It has no Microsoft Graph directory permission. The Entra administrator separately owns
app registrations, API scopes, consent, and redirect URIs. Because deployment and runtime
duties share one identity, protect the GitHub environment with branch restrictions and
required reviewers.

## Threats and controls

| Threat | Primary control | Evidence |
|---|---|---|
| URL or client-side role tampering | Server-side RBAC dependencies | API authorization tests |
| Cross-student disclosure | Object-level owner check | Negative access test |
| Stolen deployment secret | GitHub OIDC; no Azure client secret | Workflow permissions and federation |
| Credential stuffing | Persistent endpoint rate limiting; Entra MFA/Conditional Access when Microsoft sign-in is enabled | Rate-limit tests and tenant review |
| Password disclosure | Argon2id hashing; no plaintext storage or logging | Local-auth tests and database review |
| Self-service privilege escalation | Registration rejects role; inactive Student default; admin-only activation | Negative registration test |
| SQL injection | SQLAlchemy parameterization | Code review and tests |
| Secret leakage | Key Vault references and secret scanning | Terraform and CI |
| Agent prompt injection | No privileged tools; backend role selection | Agent isolation test plan |
| Hallucinated school policy | File-search grounding and explicit safe referral | Grounding evaluation |
| Assistant data leakage | PostgreSQL role boundary; no question text in audit details | Audit review |
| Direct database access | Private VNet address and no public endpoint | Terraform plan |
| Web exploits and malicious request bodies | App Service HTTPS, strict request schemas and application validation | API and negative-input tests |
| Clear-text public traffic | Azure App Service HTTPS is the documented public endpoint | Live HTTPS verification |

## Production readiness gates

Real student data is prohibited until privacy/DPIA, retention, backup restore,
penetration testing, operational ownership, Conditional Access, and incident response
are approved. Development uses synthetic records only.

Local password reset, email ownership verification, PostgreSQL-backed rate limiting and
administrator registration review are implemented for the synthetic demonstration. They
do not remove the remaining privacy, operational, resilience, accessibility, penetration
and incident-response gates.
