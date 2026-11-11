export type Role = "student" | "teacher" | "admin";

export interface PortalUser {
  id: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
  email_verified_at: string | null;
  identity_provider: "local" | "microsoft";
  created_at: string;
}

export interface InvitationResponse {
  status: "sent" | "delivery_failed";
  message: string;
  user: PortalUser;
}

export interface DashboardData {
  role: Role;
  title: string;
  summary: string;
  actions: Array<{
    title: string;
    description: string;
  }>;
  suggested_questions: string[];
}

export interface AuditEvent {
  id: string;
  occurred_at: string;
  actor_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  outcome: string;
  correlation_id: string | null;
  details_json: string;
}
