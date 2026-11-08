# Security boundary

## Identity and authorization

- Microsoft Entra ID performs authentication, MFA, recovery, and token issuance.
- The SPA requests an access token for the API using authorization code + PKCE.
- FastAPI validates signature, issuer, audience, expiry, object ID, and `access_as_user` scope.
- Portal role and active status are loaded server-side from PostgreSQL for every request.
- Students and teachers can read only their own profile. Only administrators can list or change users.
- Administrative changes are deterministic API operations and create an audit event.
- The role-specific AI endpoint selects the role on the server. An LLM is never an authorization layer.

## Managed identities

`id-mmaug-secure-login-portal` is the runtime identity. It is attached only to the
backend and receives narrowly scoped data-plane roles such as Key Vault Secrets User.

`id-mmaug-github-deploy` is reserved for deployment. Its GitHub federated credential
must trust an exact repository and GitHub environment subject. It must not be attached
to the running application.

## Threats and controls

| Threat | Primary control | Evidence |
|---|---|---|
| URL or client-side role tampering | Server-side RBAC dependencies | API authorization tests |
| Cross-student disclosure | Object-level owner check | Negative access test |
| Stolen deployment secret | GitHub OIDC; no Azure client secret | Workflow permissions and federation |
| Credential stuffing | Entra MFA/Conditional Access and smart lockout | Tenant policy review |
| SQL injection | SQLAlchemy parameterization | Code review and tests |
| Secret leakage | Key Vault references and secret scanning | Terraform and CI |
| Agent prompt injection | No privileged tools; backend role selection | Agent isolation test plan |
| Direct database access | Private VNet address and no public endpoint | Terraform plan |

## Production readiness gates

Real student data is prohibited until privacy/DPIA, retention, backup restore,
penetration testing, operational ownership, Conditional Access, and incident response
are approved. Development uses synthetic records only.
