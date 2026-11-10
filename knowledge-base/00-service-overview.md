# MMAUG High School secure portal

The MMAUG High School secure portal is a role-aware online service for students,
teachers, and administrators. Microsoft sign-in verifies identity. Signing in does not
automatically grant portal access: an administrator must enroll the account, and the
portal role is read from PostgreSQL on every protected request.

The portal provides a role-specific dashboard, approved school guidance, account
recovery links, and a role-aware assistant. The assistant explains portal navigation and
approved school procedures. It cannot change permissions, reveal private records, or
make decisions on behalf of school staff.

For access problems, users should record the enrollment reference shown after sign-in
and give it to an authorized portal administrator. Users must never enter passwords,
access tokens, security codes, or sensitive personal information into the assistant.
