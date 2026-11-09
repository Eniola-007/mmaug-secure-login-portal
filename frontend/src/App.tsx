import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useMsal } from "@azure/msal-react";
import { apiRequest } from "./api";
import { authConfigured, devAuthEnabled, loginRequest } from "./auth";
import mmaugLogo from "./assets/mmaug-logo.png";
import type { AuditEvent, DashboardData, PortalUser, Role } from "./types";

const demoUsers = [
  "student1@mmaug.example",
  "student2@mmaug.example",
  "student3@mmaug.example",
  "student4@mmaug.example",
  "student5@mmaug.example",
  "teacher1@mmaug.example",
  "teacher2@mmaug.example",
  "admin@mmaug.example",
];

type View = "dashboard" | "assistant" | "people" | "audit";

export default function App() {
  const { instance, accounts } = useMsal();
  const account = accounts[0] ?? null;
  const [devUser, setDevUser] = useState(devAuthEnabled ? demoUsers[0] : "");
  const [currentUser, setCurrentUser] = useState<PortalUser | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [users, setUsers] = useState<PortalUser[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [view, setView] = useState<View>("dashboard");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [agentMessage, setAgentMessage] = useState("");
  const [agentReply, setAgentReply] = useState("");

  const callApi = useCallback(
    <T,>(path: string, init?: RequestInit) => apiRequest<T>(path, account, devUser, init),
    [account, devUser],
  );

  const loadPortal = useCallback(async () => {
    if (!account && !devUser) return;
    setLoading(true);
    setError("");
    try {
      const [me, dashboardData] = await Promise.all([
        callApi<PortalUser>("/api/auth/me"),
        callApi<DashboardData>("/api/dashboard"),
      ]);
      setCurrentUser(me);
      setDashboard(dashboardData);
      setView("dashboard");
    } catch (caught) {
      setCurrentUser(null);
      setError(caught instanceof Error ? caught.message : "Unable to load the portal");
    } finally {
      setLoading(false);
    }
  }, [account, callApi, devUser]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadPortal(), 0);
    return () => window.clearTimeout(timer);
  }, [loadPortal]);

  async function openView(nextView: View) {
    setError("");
    setView(nextView);
    try {
      if (nextView === "people") setUsers(await callApi<PortalUser[]>("/api/users"));
      if (nextView === "audit") setEvents(await callApi<AuditEvent[]>("/api/audit-events"));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to load this page");
    }
  }

  async function updateUser(user: PortalUser, patch: { role?: Role; is_active?: boolean }) {
    const updated = await callApi<PortalUser>(`/api/users/${user.id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    });
    setUsers((items) => items.map((item) => (item.id === updated.id ? updated : item)));
  }

  async function askAgent(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const response = await callApi<{ response: string; safety_notice: string }>(
        "/api/agent/message",
        { method: "POST", body: JSON.stringify({ message: agentMessage }) },
      );
      setAgentReply(`${response.response} ${response.safety_notice}`);
      setAgentMessage("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Assistant request failed");
    }
  }

  if (!account && !devAuthEnabled) {
    return (
      <main className="login-shell">
        <section className="login-card">
          <img className="school-logo" src={mmaugLogo} alt="MMAUG school seal" />
          <p className="eyebrow">MMAUG HIGH SCHOOL</p>
          <h1>One secure place for your school day.</h1>
          <p className="muted">
            Use any Microsoft work, school, guest, or personal account. Sign-in verifies who
            you are; portal access is provided only after a school administrator enrolls you.
          </p>
          {authConfigured ? (
            <button className="primary full" onClick={() => void instance.loginRedirect({ ...loginRequest, prompt: "select_account" })}>
              Sign in with Microsoft
            </button>
          ) : (
            <div className="dev-banner" role="status">
              Deployment is live. Microsoft sign-in is pending administrator app registration.
            </div>
          )}
          <div className="recovery-links" aria-label="Account recovery">
            <a href="https://passwordreset.microsoftonline.com/">Work or school recovery</a>
            <a href="https://account.live.com/password/reset">Personal account recovery</a>
          </div>
          {error && <p className="error">{error}</p>}
        </section>
      </main>
    );
  }

  if (account && !devAuthEnabled && !currentUser && !loading && error) {
    return (
      <main className="login-shell">
        <section className="login-card access-card" role="alert">
          <img className="school-logo small" src={mmaugLogo} alt="MMAUG school seal" />
          <p className="eyebrow">SIGN-IN COMPLETE</p>
          <h1>Your identity is verified.</h1>
          <p className="signed-in-as">Signed in as <strong>{account.username}</strong></p>
          <p className="access-message">{error}</p>
          <button className="primary full" onClick={() => void instance.logoutRedirect()}>
            Sign out and use another account
          </button>
        </section>
      </main>
    );
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><img className="brand-logo" src={mmaugLogo} alt="" /><span>MMAUG<br /><small>HIGH SCHOOL</small></span></div>
        <nav aria-label="Portal navigation">
          <button className={view === "dashboard" ? "active" : ""} onClick={() => void openView("dashboard")}>Overview</button>
          <button className={view === "assistant" ? "active" : ""} onClick={() => void openView("assistant")}>My assistant</button>
          {currentUser?.role === "admin" && (
            <>
              <button className={view === "people" ? "active" : ""} onClick={() => void openView("people")}>People & access</button>
              <button className={view === "audit" ? "active" : ""} onClick={() => void openView("audit")}>Audit activity</button>
            </>
          )}
        </nav>
        <div className="sidebar-footer"><span className="status-dot" /> Secure session</div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">SECURE PORTAL</p>
            <h2>{currentUser ? `Welcome, ${currentUser.display_name.split(" ")[0]}` : "Loading portal"}</h2>
          </div>
          <div className="account-area">
            {devAuthEnabled && (
              <label className="dev-switcher">Demo identity
                <select value={devUser} onChange={(event) => setDevUser(event.target.value)}>
                  {demoUsers.map((email) => <option key={email}>{email}</option>)}
                </select>
              </label>
            )}
            {currentUser && <span className={`role-pill ${currentUser.role}`}>{currentUser.role}</span>}
            {account && <button className="quiet" onClick={() => void instance.logoutRedirect()}>Sign out</button>}
          </div>
        </header>

        {devAuthEnabled && <div className="dev-banner">Development authentication is active. Never enable this setting in UAT or production.</div>}
        {error && <div className="error-banner" role="alert">{error}</div>}
        {loading && <div className="loading">Checking your access…</div>}

        {!loading && currentUser && view === "dashboard" && dashboard && (
          <section>
            <div className="hero-panel">
              <div><p className="eyebrow">YOUR SPACE</p><h1>{dashboard.title}</h1><p>Tools and information shown here are limited to your approved role.</p></div>
              <div className="shield" aria-hidden="true">✓</div>
            </div>
            <div className="card-grid">
              {dashboard.actions.map((action, index) => (
                <article className="feature-card" key={action}><span className="card-number">0{index + 1}</span><h3>{action}</h3><p>Access is checked by the API before any information is returned.</p></article>
              ))}
              <article className="feature-card accent"><span className="card-number">AI</span><h3>Role-aware assistant</h3><p>Designed to stay inside your approved information boundary.</p><button className="text-button" onClick={() => void openView("assistant")}>Open assistant →</button></article>
            </div>
          </section>
        )}

        {currentUser && view === "assistant" && (
          <section className="panel narrow">
            <p className="eyebrow">{currentUser.role.toUpperCase()} ASSISTANT</p>
            <h1>How can I help?</h1>
            <p className="muted">Do not enter passwords, access tokens, or personal information.</p>
            <form className="assistant-form" onSubmit={(event) => void askAgent(event)}>
              <textarea value={agentMessage} onChange={(event) => setAgentMessage(event.target.value)} maxLength={2000} required placeholder="Ask about approved school resources…" />
              <button className="primary" type="submit">Send securely</button>
            </form>
            {agentReply && <div className="agent-reply">{agentReply}</div>}
          </section>
        )}

        {currentUser?.role === "admin" && view === "people" && (
          <section className="panel">
            <div className="section-heading"><div><p className="eyebrow">ADMINISTRATION</p><h1>People & access</h1></div><span>{users.length} accounts</span></div>
            <div className="table-wrap"><table><thead><tr><th>Name</th><th>Role</th><th>Status</th><th>Controls</th></tr></thead><tbody>
              {users.map((user) => <tr key={user.id}><td><strong>{user.display_name}</strong><small>{user.email}</small></td><td><span className={`role-pill ${user.role}`}>{user.role}</span></td><td>{user.is_active ? "Active" : "Inactive"}</td><td className="controls"><select aria-label={`Role for ${user.display_name}`} value={user.role} onChange={(event) => void updateUser(user, { role: event.target.value as Role })}><option value="student">Student</option><option value="teacher">Teacher</option><option value="admin">Administrator</option></select><button className="quiet" onClick={() => void updateUser(user, { is_active: !user.is_active })}>{user.is_active ? "Deactivate" : "Activate"}</button></td></tr>)}
            </tbody></table></div>
          </section>
        )}

        {currentUser?.role === "admin" && view === "audit" && (
          <section className="panel">
            <div className="section-heading"><div><p className="eyebrow">SECURITY</p><h1>Audit activity</h1></div><span>Latest {events.length}</span></div>
            <div className="event-list">{events.map((event) => <article key={event.id}><span className={`outcome ${event.outcome}`} /> <div><strong>{event.action}</strong><p>{new Date(event.occurred_at).toLocaleString()} · {event.target_type ?? "portal"}</p></div></article>)}</div>
          </section>
        )}
      </main>
    </div>
  );
}
