# Bootstrap the first portal administrator

The portal does not allow a pending user to promote themselves. The first Administrator
is created by an operator who already has authorized access to the Azure API App Service.
Every later approval and role change is performed in the portal and written to the audit
log.

## 1. Complete Microsoft sign-in configuration

The Entra administrator creates the SPA/API registrations, configures the SPA redirect
URI, grants the API's delegated `access_as_user` scope, and returns both client IDs. Store
the IDs as GitHub `development` **environment variables** named `ENTRA_SPA_CLIENT_ID` and
`ENTRA_API_CLIENT_ID`, then rerun **Deploy development**.

Client IDs are identifiers, not secrets. The existing `AZURE_AD_*` environment secrets
are for the approved Foundry service principal and do not configure browser MSAL.

## 2. Copy your immutable identity values

Use either source:

1. Sign in to the portal with Microsoft. If you are not enrolled, copy the displayed
   enrollment reference in the form `<tenant-id>:<object-id>`; or
2. In Azure portal, open **Microsoft Entra ID → Users → your account → Overview** and copy
   **Tenant ID** and **Object ID**.

For this project, the home tenant ID is
`71beefd7-29f4-4b9e-9cb2-e78b5dc851ad`. Always use the real Object ID shown for the
identity that will sign in; do not use an application/client ID.

## 3. Map yourself to the Administrator database role

1. In Azure portal, open **App Services**.
2. Select `app-mmaug-development-api-gkt6d`.
3. Select **Development Tools → SSH**, then **Go**.
4. In the App Service shell, go to the deployed application:

   ```bash
   cd /home/site/wwwroot
   ```

5. Validate the mapping without saving it. Replace all angle-bracket values:

   ```bash
   python -m app.enroll_users \
     --tenant-id 71beefd7-29f4-4b9e-9cb2-e78b5dc851ad \
     --object-id <your-user-object-id> \
     --email <your-sign-in-email> \
     --display-name "<your-name>" \
     --role admin \
     --dry-run
   ```

6. Confirm the output says one record was validated. Run the same command again without
   `--dry-run`.
7. Sign out of the portal, sign in again, and confirm the left navigation shows
   **People & access** and **Audit activity**.

This command is idempotent: rerunning it with the same identity updates that one user. It
does not grant an Entra directory role or an Azure RBAC role; it grants only the MMAUG
application's PostgreSQL `admin` role.

## 4. Approve other users

1. Open **Administrator dashboard → People & access**.
2. Confirm a local account says **Email verified**, or that a Microsoft account says
   **Microsoft verified**.
3. Choose **Student**, **Teacher**, or **Administrator** in **Database role**.
4. Select **Approve & activate**.
5. Open **Audit activity** and confirm `user access updated` was recorded.

Use Administrator only for staff who are authorized to approve accounts and change portal
roles. Users cannot activate themselves, and the assistant cannot make role changes.
