# Administrator guidance

Administrators can use the portal to review enrolled accounts, assign the application
roles student, teacher, and administrator, activate or deactivate portal access, and
review audit activity. Role assignments are stored in PostgreSQL and enforced by the
FastAPI service. Browser input and token role claims are not treated as the portal's
authorization source.

The administrator assistant can explain approved procedures and diagnostic steps. It
cannot execute a role change, bypass approval, expose credentials, reveal raw tokens,
alter audit history, or make policy decisions. Privileged changes must use the audited
portal controls and remain subject to human confirmation.
