# Query and assign portal database roles

PostgreSQL is the source of truth for MMAUG portal roles. The supported administrative
interface is the authenticated portal, not direct public database access. The PostgreSQL
Flexible Server uses private networking, and its password remains in Key Vault.

## Query users and roles

1. Open `https://app-mmaug-development-web-gkt6d.azurewebsites.net`.
2. Sign in with an active account whose PostgreSQL role is `admin`.
3. Select **People & access** in the left navigation.
4. The page queries `GET /api/users` and displays each person's email, database role,
   identity-verification state, and activation state.
5. Use **Audit activity** to query the latest role and activation changes.

The API only returns the user list to an authenticated database Administrator. Students
and Teachers receive HTTP 403.

## Assign a role

1. In **People & access**, find the user by their exact email address.
2. Confirm **Email verified** for a local account or **Microsoft verified** for an Entra
   account.
3. Select **Student**, **Teacher**, or **Administrator** under **Database role**.
4. Select **Approve & activate** if the account is pending.
5. Open **Audit activity** and confirm `user access updated` was recorded.
6. Ask the user to sign out and sign in again so a fresh session reflects the new role.

Active Administrators receive an email with subject **MMAUG account verified and ready for
review** as soon as the account completes verification. The notification does not approve
the account; the Administrator must still review and activate it in **People & access**.

The API rejects role assignment or activation for an unverified local account. Use
Administrator only for authorized staff who may approve users and change roles.

## SQL reference for an authorized private-network operator

Do not enable PostgreSQL public access just to run these queries. If an approved operator
already has a client inside the private network, the equivalent read-only query is:

```sql
SELECT
    email,
    display_name,
    role,
    is_active,
    email_verified_at,
    entra_tenant_id,
    entra_object_id,
    updated_at
FROM users
ORDER BY role, display_name;
```

To inspect one account:

```sql
SELECT email, role, is_active, email_verified_at
FROM users
WHERE lower(email) = lower('person@example.com');
```

Direct `UPDATE` statements bypass the application's verification checks and audit event,
so role changes must normally be made through **People & access**.
