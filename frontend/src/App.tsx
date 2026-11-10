import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useMsal } from "@azure/msal-react";
import { apiRequest, publicApiRequest } from "./api";
import { authConfigured, devAuthEnabled, loginRequest } from "./auth";
import mmaugLogo from "./assets/mmaug-logo.png";
import type { AuditEvent, DashboardData, PortalUser, Role } from "./types";

const demoUsers = [
  "student1@mmaug.example", "student2@mmaug.example", "student3@mmaug.example",
  "student4@mmaug.example", "student5@mmaug.example", "teacher1@mmaug.example",
  "teacher2@mmaug.example", "admin@mmaug.example",
];

const roleExperience: Record<Role, {
  label: string; greeting: string; focus: string;
  metrics: Array<{ value: string; label: string }>;
  agenda: Array<{ time: string; title: string; meta: string }>;
}> = {
  student: {
    label: "Student workspace", greeting: "Your learning day, clearly organised.",
    focus: "Find approved learning resources, school notices, and help without leaving your secure space.",
    metrics: [{ value: "Ready", label: "Portal access" }, { value: "Private", label: "Role workspace" }, { value: "On hand", label: "Guidance available" }],
    agenda: [{ time: "Start here", title: "Review school announcements", meta: "Approved notices" }, { time: "Next", title: "Open the learning hub", meta: "Study resources" }, { time: "Any time", title: "Ask the student assistant", meta: "Safe school guidance" }],
  },
  teacher: {
    label: "Teacher workspace", greeting: "Teaching tools with privacy built in.",
    focus: "Move between classroom guidance, approved resources, and school procedures from one calm workspace.",
    metrics: [{ value: "Ready", label: "Class workspace" }, { value: "Curated", label: "Resource access" }, { value: "Guarded", label: "AI assistance" }],
    agenda: [{ time: "Plan", title: "Review classroom guidance", meta: "Teaching workflow" }, { time: "Prepare", title: "Browse approved resources", meta: "Resource library" }, { time: "Support", title: "Ask the teacher assistant", meta: "No student records exposed" }],
  },
  admin: {
    label: "Administrator workspace", greeting: "School access, visible and accountable.",
    focus: "Approve accounts, assign database roles, review audit activity, and keep portal access under control.",
    metrics: [{ value: "DB", label: "Role authority" }, { value: "Logged", label: "Access changes" }, { value: "Live", label: "Service monitoring" }],
    agenda: [{ time: "Review", title: "Check pending accounts", meta: "People & access" }, { time: "Verify", title: "Review recent role changes", meta: "Audit activity" }, { time: "Monitor", title: "Confirm service health", meta: "Operations" }],
  },
};

type View = "dashboard" | "assistant" | "people" | "audit";
type AuthMode = "signin" | "signup" | "forgot" | "reset";
interface TokenResponse { access_token: string; token_type: string; expires_in: number }
interface RegistrationResponse { status: string; message: string }

function MicrosoftMark() {
  return <span className="microsoft-mark" aria-hidden="true"><i /><i /><i /><i /></span>;
}

function ArrowIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h13M13 6l6 6-6 6" /></svg>;
}

function PortalIcon({ name }: { name: "home" | "spark" | "people" | "audit" | "bell" | "shield" }) {
  const paths = {
    home: <><path d="m3 11 9-7 9 7" /><path d="M5 10v10h14V10M9 20v-6h6v6" /></>,
    spark: <><path d="m12 3 1.4 4.1L17 9l-3.6 1.9L12 15l-1.4-4.1L7 9l3.6-1.9L12 3Z" /><path d="m18.5 15 .8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2Z" /></>,
    people: <><circle cx="9" cy="8" r="3" /><path d="M3.5 20v-2.2c0-2.6 2.1-4.8 4.8-4.8h1.4c2.7 0 4.8 2.2 4.8 4.8V20" /><path d="M15 5.5a3 3 0 0 1 0 5.7M16.5 14c2.3.3 4 2.2 4 4.5V20" /></>,
    audit: <><path d="M5 3h14v18H5z" /><path d="M8 8h8M8 12h8M8 16h5" /></>,
    bell: <><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 7h18s-3 0-3-7" /><path d="M10 20h4" /></>,
    shield: <><path d="M12 3 20 6v5c0 5-3.2 8.5-8 10-4.8-1.5-8-5-8-10V6l8-3Z" /><path d="m8.5 12 2.2 2.2 4.8-5" /></>,
  };
  return <svg className="portal-icon" viewBox="0 0 24 24" aria-hidden="true">{paths[name]}</svg>;
}

function AuthDialog({ mode, onModeChange, onClose, onLocalLogin, onLocalRegister, onForgotPassword, onResetPassword, onMicrosoft, authReady, busy, message, error }: {
  mode: AuthMode; onModeChange: (mode: AuthMode) => void; onClose: () => void;
  onLocalLogin: (email: string, password: string) => Promise<void>;
  onLocalRegister: (name: string, email: string, password: string) => Promise<void>;
  onForgotPassword: (email: string) => Promise<void>;
  onResetPassword: (password: string) => Promise<void>;
  onMicrosoft: () => void; authReady: boolean; busy: boolean; message: string; error: string;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault();
    if (mode === "signup") await onLocalRegister(name, email, password);
    else if (mode === "forgot") await onForgotPassword(email);
    else if (mode === "reset") await onResetPassword(password);
    else await onLocalLogin(email, password);
  }
  const title = mode === "signup" ? "Create your account" : mode === "forgot" ? "Recover your account" : mode === "reset" ? "Choose a new password" : "Welcome back";
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="auth-dialog" role="dialog" aria-modal="true" aria-labelledby="auth-title">
        <button className="dialog-close" type="button" onClick={onClose} aria-label="Close">×</button>
        <img src={mmaugLogo} alt="" className="dialog-logo" />
        <p className="eyebrow">MMAUG SECURE PORTAL</p>
        <h2 id="auth-title">{title}</h2>
        <p className="dialog-intro">{mode === "signup" ? "Use Microsoft or create an account with your email. Verify your email before a school administrator approves your role." : mode === "forgot" ? "Enter the email for your local portal account. We will send a short-lived recovery link if it is eligible." : mode === "reset" ? "Use at least 12 characters. Resetting your password signs out existing local sessions." : "Continue with Microsoft or sign in with an approved, verified portal account."}</p>
        {(mode === "signin" || mode === "signup") && <><div className="auth-tabs" role="tablist" aria-label="Account action"><button type="button" role="tab" aria-selected={mode === "signin"} className={mode === "signin" ? "active" : ""} onClick={() => onModeChange("signin")}>Sign in</button><button type="button" role="tab" aria-selected={mode === "signup"} className={mode === "signup" ? "active" : ""} onClick={() => onModeChange("signup")}>Sign up</button></div>
        <button className="microsoft-button" type="button" disabled={!authReady || busy} onClick={onMicrosoft}><MicrosoftMark /> {mode === "signup" ? "Sign up with Microsoft" : "Continue with Microsoft"}</button>
        {!authReady && <p className="auth-note">Microsoft sign-in will be enabled when the administrator completes the app registration.</p>}
        <div className="or-divider"><span>or use email</span></div></>}
        <form className="auth-form" onSubmit={(event) => void submit(event)}>
          {mode === "signup" && <label>Full name<input value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={160} autoComplete="name" required /></label>}
          {mode !== "reset" && <label>Email address<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" required /></label>}
          {mode !== "forgot" && <label>{mode === "reset" ? "New password" : "Password"}<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} minLength={mode === "signup" || mode === "reset" ? 12 : 1} maxLength={128} autoComplete={mode === "signup" || mode === "reset" ? "new-password" : "current-password"} required /></label>}
          {mode === "signup" && <p className="password-hint">Use at least 12 characters. You must verify your email; only a school administrator can activate or change a role.</p>}
          {message && <div className="success-message" role="status">{message}</div>}
          {error && <div className="form-error" role="alert">{error}</div>}
          <button className="primary full" type="submit" disabled={busy}>{busy ? "Please wait…" : mode === "signup" ? "Request my account" : mode === "forgot" ? "Send recovery link" : mode === "reset" ? "Reset password" : "Sign in securely"}</button>
          {mode === "signin" && <button className="text-action" type="button" onClick={() => onModeChange("forgot")}>Forgot your local password?</button>}
          {(mode === "forgot" || mode === "reset") && <button className="text-action" type="button" onClick={() => onModeChange("signin")}>Back to sign in</button>}
        </form>
      </section>
    </div>
  );
}

function PublicLanding({ openAuth, onMicrosoftRegistration, onMicrosoftSignout, microsoftEmail, accessError, accessMessage, loading }: {
  openAuth: (mode: AuthMode) => void; onMicrosoftRegistration: () => void; onMicrosoftSignout: () => void;
  microsoftEmail: string; accessError: string; accessMessage: string; loading: boolean;
}) {
  return (
    <div className="public-site">
      <header className="public-header">
        <a className="public-brand" href="#top" aria-label="MMAUG High School home"><img src={mmaugLogo} alt="" /><span>MMAUG <small>HIGH SCHOOL</small></span></a>
        <nav className="public-nav" aria-label="Public navigation"><a href="#experience">Portal experience</a><a href="#community">Our community</a><a href="#security">Security</a></nav>
        <div className="header-actions"><button className="link-button" onClick={() => openAuth("signin")}>Sign in</button><button className="primary compact" onClick={() => openAuth("signup")}>Create account</button></div>
      </header>
      <main id="top">
        {(microsoftEmail || accessMessage) && <section className="access-notice" aria-live="polite"><div><span className="notice-icon"><PortalIcon name="shield" /></span><div><strong>{accessMessage ? "Account request received" : "Microsoft identity verified"}</strong><p>{accessMessage || accessError || `Signed in as ${microsoftEmail}. Request access so an administrator can assign your portal role.`}</p></div></div><div className="notice-actions">{!accessMessage && accessError.includes("not enrolled") && <button className="primary compact" disabled={loading} onClick={onMicrosoftRegistration}>{loading ? "Sending…" : "Request portal access"}</button>}{microsoftEmail && <button className="quiet" onClick={onMicrosoftSignout}>Use another account</button>}</div></section>}
        <section className="landing-hero">
          <div className="hero-copy"><p className="eyebrow light">LEARN. INNOVATE. BUILD.</p><h1>One school day.<br /><em>Beautifully connected.</em></h1><p className="hero-lead">A welcoming digital home for MMAUG students, teachers, and administrators—designed to keep learning simple and access secure.</p><div className="hero-actions"><button className="primary large" onClick={() => openAuth("signup")}>Join the portal <ArrowIcon /></button><button className="outline-light" onClick={() => openAuth("signin")}>I already have an account</button></div><div className="hero-trust"><span><PortalIcon name="shield" /> Roles approved by school administrators</span><span>Microsoft and email accounts supported</span></div></div>
          <div className="hero-showcase" aria-label="Portal preview"><div className="showcase-glow" /><div className="mini-dashboard"><div className="mini-sidebar"><img src={mmaugLogo} alt="" /><span /><span /><span /></div><div className="mini-main"><div className="mini-top"><small>GOOD MORNING</small><i /></div><h3>Your day at a glance</h3><div className="mini-welcome"><span>WELCOME BACK</span><strong>Everything you need,<br />right where you need it.</strong></div><div className="mini-cards"><i /><i /><i /></div></div></div><div className="floating-card float-ai"><span><PortalIcon name="spark" /></span><div><small>ROLE-AWARE ASSISTANT</small><strong>How can I help today?</strong></div></div><div className="floating-card float-safe"><span><PortalIcon name="shield" /></span><div><small>ACCESS</small><strong>Protected by your role</strong></div></div></div>
        </section>
        <section className="intro-strip" id="experience"><p className="eyebrow">THE MMAUG EXPERIENCE</p><h2>Made for every part of the school community.</h2><p>Each person enters a workspace shaped around what they need—while PostgreSQL remains the source of truth for every role.</p></section>
        <section className="audience-grid" id="community">
          <article className="audience-card student-card"><div className="audience-number">01</div><div className="audience-art"><span>STUDENT</span><div className="book-stack"><i /><i /><i /></div></div><h3>For students</h3><p>Learning links, announcements, profile information, and a safe assistant in one focused place.</p><button onClick={() => openAuth("signup")}>Explore your space <ArrowIcon /></button></article>
          <article className="audience-card teacher-card"><div className="audience-number">02</div><div className="audience-art"><span>TEACHER</span><div className="teacher-lines"><i /><i /><i /><i /></div></div><h3>For teachers</h3><p>Approved classroom resources, teaching guidance, and privacy-aware assistance without exposing student records.</p><button onClick={() => openAuth("signup")}>Enter the workspace <ArrowIcon /></button></article>
          <article className="audience-card admin-card"><div className="audience-number">03</div><div className="audience-art"><span>ADMIN</span><div className="admin-grid"><i /><i /><i /><i /></div></div><h3>For administrators</h3><p>Account approval, database role assignment, audit activity, and service oversight from a clear control centre.</p><button onClick={() => openAuth("signin")}>Manage securely <ArrowIcon /></button></article>
        </section>
        <section className="assistant-story"><div className="assistant-orbit"><div className="orbit-ring"><img src={mmaugLogo} alt="MMAUG" /></div><span className="orbit-chip chip-one">STUDENT</span><span className="orbit-chip chip-two">TEACHER</span><span className="orbit-chip chip-three">ADMIN</span></div><div className="assistant-copy"><p className="eyebrow light">YOUR SCHOOL GUIDE</p><h2>Helpful answers.<br />Clear boundaries.</h2><p>The MMAUG assistant welcomes every approved user and answers from the school knowledge base for their assigned role. Guardrails keep it within school guidance—it cannot change permissions or reveal another person’s records.</p><div className="assistant-points"><span><i>✓</i> Answers from approved school information</span><span><i>✓</i> Different guidance for each role</span><span><i>✓</i> Human oversight for important decisions</span></div><button className="primary large" onClick={() => openAuth("signup")}>Get started <ArrowIcon /></button></div></section>
        <section className="security-section" id="security"><div><p className="eyebrow">SECURITY BY DESIGN</p><h2>Your identity opens the door.<br />The database decides the room.</h2></div><div className="security-steps"><article><span>1</span><div><strong>Choose how to sign in</strong><p>Use a Microsoft account or create a portal account with email and password.</p></div></article><article><span>2</span><div><strong>An administrator approves access</strong><p>New registrations cannot select privileged roles or activate themselves.</p></div></article><article><span>3</span><div><strong>Your dashboard follows your DB role</strong><p>Student, Teacher, and Administrator permissions are enforced by the API.</p></div></article></div></section>
        <section className="closing-cta"><img src={mmaugLogo} alt="" /><p className="eyebrow light">WELCOME TO MMAUG HIGH SCHOOL</p><h2>Ready to begin your school day?</h2><p>Create an account with or without Microsoft. Your administrator will approve the right workspace.</p><div><button className="primary large" onClick={() => openAuth("signup")}>Create your account</button><button className="link-light" onClick={() => openAuth("signin")}>Sign in instead →</button></div></section>
      </main>
      <footer className="public-footer"><a className="public-brand" href="#top"><img src={mmaugLogo} alt="" /><span>MMAUG <small>HIGH SCHOOL</small></span></a><p>Learn. Innovate. Build.</p><div><a href="https://passwordreset.microsoftonline.com/">Microsoft account recovery</a><span>Secure school portal</span></div></footer>
    </div>
  );
}

export default function App() {
  const { instance, accounts } = useMsal();
  const account = accounts[0] ?? null;
  const [devUser, setDevUser] = useState(devAuthEnabled ? demoUsers[0] : "");
  const [localToken, setLocalToken] = useState(() => sessionStorage.getItem("mmaug-local-token") ?? "");
  const [currentUser, setCurrentUser] = useState<PortalUser | null>(null);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [users, setUsers] = useState<PortalUser[]>([]);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [view, setView] = useState<View>("dashboard");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [agentMessage, setAgentMessage] = useState("");
  const [agentReply, setAgentReply] = useState("");
  const [authMode, setAuthMode] = useState<AuthMode | null>(null);
  const [authBusy, setAuthBusy] = useState(false);
  const [authMessage, setAuthMessage] = useState("");
  const [authError, setAuthError] = useState("");
  const [accessMessage, setAccessMessage] = useState("");
  const [resetToken, setResetToken] = useState("");
  const recoveryHandled = useRef(false);

  const callApi = useCallback(<T,>(path: string, init?: RequestInit) => apiRequest<T>(path, account, devUser, localToken, init), [account, devUser, localToken]);
  const loadPortal = useCallback(async () => {
    if (!account && !devUser && !localToken) return;
    setLoading(true); setError("");
    try {
      const [me, dashboardData] = await Promise.all([callApi<PortalUser>("/api/auth/me"), callApi<DashboardData>("/api/dashboard")]);
      setCurrentUser(me); setDashboard(dashboardData); setView("dashboard");
    } catch (caught) { setCurrentUser(null); setError(caught instanceof Error ? caught.message : "Unable to load the portal"); }
    finally { setLoading(false); }
  }, [account, callApi, devUser, localToken]);

  useEffect(() => { const timer = window.setTimeout(() => void loadPortal(), 0); return () => window.clearTimeout(timer); }, [loadPortal]);
  useEffect(() => {
    if (recoveryHandled.current) return;
    recoveryHandled.current = true;
    let timer = 0;
    const parameters = new URLSearchParams(window.location.search);
    const verificationToken = parameters.get("verify_email");
    const passwordToken = parameters.get("reset_password");
    if (verificationToken) {
      parameters.delete("verify_email");
      window.history.replaceState({}, "", `${window.location.pathname}${parameters.size ? `?${parameters}` : ""}${window.location.hash}`);
      timer = window.setTimeout(() => {
        setAuthMode("signin"); setAuthBusy(true); setAuthError("");
        void publicApiRequest<RegistrationResponse>("/api/auth/verify-email", { method: "POST", body: JSON.stringify({ token: verificationToken }) })
          .then((response) => setAuthMessage(response.message))
          .catch((caught: unknown) => setAuthError(caught instanceof Error ? caught.message : "Email verification failed"))
          .finally(() => setAuthBusy(false));
      }, 0);
    } else if (passwordToken) {
      parameters.delete("reset_password");
      window.history.replaceState({}, "", `${window.location.pathname}${parameters.size ? `?${parameters}` : ""}${window.location.hash}`);
      timer = window.setTimeout(() => { setResetToken(passwordToken); setAuthMode("reset"); }, 0);
    }
    return () => window.clearTimeout(timer);
  }, []);
  function openAuth(mode: AuthMode) { setAuthMode(mode); setAuthMessage(""); setAuthError(""); }

  async function localLogin(email: string, password: string) {
    setAuthBusy(true); setAuthError("");
    try {
      const response = await publicApiRequest<TokenResponse>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
      sessionStorage.setItem("mmaug-local-token", response.access_token); setLocalToken(response.access_token); setAuthMode(null);
    } catch (caught) { setAuthError(caught instanceof Error ? caught.message : "Sign-in failed"); }
    finally { setAuthBusy(false); }
  }

  async function localRegister(name: string, email: string, password: string) {
    setAuthBusy(true); setAuthError(""); setAuthMessage("");
    try {
      const response = await publicApiRequest<RegistrationResponse>("/api/auth/register", { method: "POST", body: JSON.stringify({ display_name: name, email, password }) });
      setAuthMessage(response.message);
    } catch (caught) { setAuthError(caught instanceof Error ? caught.message : "Registration failed"); }
    finally { setAuthBusy(false); }
  }

  async function forgotPassword(email: string) {
    setAuthBusy(true); setAuthError(""); setAuthMessage("");
    try {
      const response = await publicApiRequest<RegistrationResponse>("/api/auth/forgot-password", { method: "POST", body: JSON.stringify({ email }) });
      setAuthMessage(response.message);
    } catch (caught) { setAuthError(caught instanceof Error ? caught.message : "Recovery request failed"); }
    finally { setAuthBusy(false); }
  }

  async function resetPassword(password: string) {
    setAuthBusy(true); setAuthError(""); setAuthMessage("");
    try {
      const response = await publicApiRequest<RegistrationResponse>("/api/auth/reset-password", { method: "POST", body: JSON.stringify({ token: resetToken, password }) });
      setResetToken(""); setAuthMode("signin"); setAuthMessage(response.message);
    } catch (caught) { setAuthError(caught instanceof Error ? caught.message : "Password reset failed"); }
    finally { setAuthBusy(false); }
  }

  async function requestMicrosoftRegistration() {
    setLoading(true);
    try { const response = await callApi<RegistrationResponse>("/api/auth/register-microsoft", { method: "POST" }); setAccessMessage(response.message); setError(""); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to request access"); }
    finally { setLoading(false); }
  }

  function signOut() {
    if (account) { void instance.logoutRedirect(); return; }
    sessionStorage.removeItem("mmaug-local-token"); setLocalToken(""); setCurrentUser(null); setDashboard(null); setError("");
  }

  async function openView(nextView: View) {
    setError(""); setView(nextView);
    try { if (nextView === "people") setUsers(await callApi<PortalUser[]>("/api/users")); if (nextView === "audit") setEvents(await callApi<AuditEvent[]>("/api/audit-events")); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to load this page"); }
  }

  async function updateUser(user: PortalUser, patch: { role?: Role; is_active?: boolean }) {
    try { const updated = await callApi<PortalUser>(`/api/users/${user.id}`, { method: "PATCH", body: JSON.stringify(patch) }); setUsers((items) => items.map((item) => item.id === updated.id ? updated : item)); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Unable to update this account"); }
  }

  async function askAgent(event: FormEvent) {
    event.preventDefault(); setError("");
    try { const response = await callApi<{ response: string; safety_notice: string }>("/api/agent/message", { method: "POST", body: JSON.stringify({ message: agentMessage }) }); setAgentReply(`${response.response} ${response.safety_notice}`); setAgentMessage(""); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Assistant request failed"); }
  }

  function askSuggested(question: string) { setAgentMessage(question); setView("assistant"); }
  const experience = useMemo(() => currentUser ? roleExperience[currentUser.role] : null, [currentUser]);

  if (!currentUser) {
    return <><PublicLanding openAuth={openAuth} onMicrosoftRegistration={() => void requestMicrosoftRegistration()} onMicrosoftSignout={() => void instance.logoutRedirect()} microsoftEmail={account?.username ?? ""} accessError={error} accessMessage={accessMessage} loading={loading} />{authMode && <AuthDialog key={authMode} mode={authMode} onModeChange={(mode) => { setAuthMode(mode); setAuthError(""); setAuthMessage(""); }} onClose={() => setAuthMode(null)} onLocalLogin={localLogin} onLocalRegister={localRegister} onForgotPassword={forgotPassword} onResetPassword={resetPassword} onMicrosoft={() => void instance.loginRedirect({ ...loginRequest, prompt: "select_account" })} authReady={authConfigured} busy={authBusy} message={authMessage} error={authError} />}</>;
  }

  return (
    <div className={`app-shell role-${currentUser.role}`}>
      <aside className="sidebar"><div className="brand"><img className="brand-logo" src={mmaugLogo} alt="" /><span>MMAUG<br /><small>HIGH SCHOOL</small></span></div><div className="workspace-label"><small>YOUR WORKSPACE</small><strong>{experience?.label}</strong></div><nav aria-label="Portal navigation"><button className={view === "dashboard" ? "active" : ""} onClick={() => void openView("dashboard")}><PortalIcon name="home" /> Overview</button><button className={view === "assistant" ? "active" : ""} onClick={() => void openView("assistant")}><PortalIcon name="spark" /> My assistant</button>{currentUser.role === "admin" && <><button className={view === "people" ? "active" : ""} onClick={() => void openView("people")}><PortalIcon name="people" /> People & access</button><button className={view === "audit" ? "active" : ""} onClick={() => void openView("audit")}><PortalIcon name="audit" /> Audit activity</button></>}</nav><div className="sidebar-help"><PortalIcon name="shield" /><div><strong>Protected workspace</strong><small>Access follows your database role.</small></div></div><div className="sidebar-footer"><span className="status-dot" /> Secure session</div></aside>
      <main className="main-content">
        <header className="topbar"><div><p className="eyebrow">{new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" }).toUpperCase()}</p><h2>Welcome, {currentUser.display_name.split(" ")[0]}</h2></div><div className="account-area">{devAuthEnabled && <label className="dev-switcher">Demo identity<select value={devUser} onChange={(event) => setDevUser(event.target.value)}>{demoUsers.map((email) => <option key={email}>{email}</option>)}</select></label>}<button className="icon-button" aria-label="Notifications"><PortalIcon name="bell" /></button><div className="user-chip"><span>{currentUser.display_name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</span><div><strong>{currentUser.display_name}</strong><small>{experience?.label}</small></div></div>{!devAuthEnabled && <button className="quiet" onClick={signOut}>Sign out</button>}</div></header>
        {devAuthEnabled && <div className="dev-banner">Development authentication is active. Never enable this setting in UAT or production.</div>}{error && <div className="error-banner" role="alert">{error}</div>}{loading && <div className="loading">Checking your access…</div>}
        {!loading && view === "dashboard" && dashboard && experience && <section className="dashboard-page"><div className="dashboard-hero"><div className="dashboard-hero-copy"><span className={`role-pill ${currentUser.role}`}>{currentUser.role}</span><h1>{experience.greeting}</h1><p>{experience.focus}</p><button onClick={() => void openView("assistant")}>Ask your assistant <ArrowIcon /></button></div><div className="dashboard-seal"><div><img src={mmaugLogo} alt="" /><span>SECURE<br />PORTAL</span></div></div></div><div className="metric-grid">{experience.metrics.map((metric) => <article key={metric.label}><strong>{metric.value}</strong><span>{metric.label}</span></article>)}</div><div className="dashboard-columns"><section className="workspace-section"><div className="section-title"><div><p className="eyebrow">YOUR WORKSPACE</p><h2>{dashboard.title}</h2></div><span>Assigned from PostgreSQL</span></div><div className="action-grid">{dashboard.actions.map((action, index) => <article key={action.title}><span className="action-index">0{index + 1}</span><div className="action-icon"><PortalIcon name={index === 0 ? "people" : index === 1 ? "home" : "bell"} /></div><h3>{action.title}</h3><p>{action.description}</p><button aria-label={`Open ${action.title}`}><ArrowIcon /></button></article>)}</div></section><aside className="today-panel"><div className="section-title"><div><p className="eyebrow">A GOOD PLACE TO START</p><h2>Today</h2></div><span className="today-date">{new Date().getDate()}</span></div><div className="agenda-list">{experience.agenda.map((item) => <article key={item.title}><span>{item.time}</span><div><strong>{item.title}</strong><small>{item.meta}</small></div></article>)}</div></aside></div><section className="assistant-banner"><div className="assistant-avatar"><PortalIcon name="spark" /></div><div><p className="eyebrow light">MMAUG ASSISTANT</p><h2>What would you like help with?</h2><p>I use approved guidance for your {currentUser.role} role and stay inside the school’s guardrails.</p></div><div className="assistant-suggestions">{dashboard.suggested_questions.map((question) => <button key={question} onClick={() => askSuggested(question)}>{question}<ArrowIcon /></button>)}</div></section></section>}
        {view === "assistant" && <section className="panel assistant-panel"><div className="assistant-heading"><span><PortalIcon name="spark" /></span><div><p className="eyebrow">{currentUser.role.toUpperCase()} ASSISTANT</p><h1>Welcome. How can I help?</h1></div></div><p className="muted">I answer from approved MMAUG guidance for your database-assigned role. Do not enter passwords, access tokens, or personal information.</p><form className="assistant-form" onSubmit={(event) => void askAgent(event)}><textarea value={agentMessage} onChange={(event) => setAgentMessage(event.target.value)} maxLength={2000} required placeholder="Ask about approved school resources…" /><div><small>School guidance only · Human review for important decisions</small><button className="primary" type="submit">Send securely <ArrowIcon /></button></div></form>{agentReply && <div className="agent-reply">{agentReply}</div>}</section>}
        {currentUser.role === "admin" && view === "people" && <section className="panel"><div className="section-heading"><div><p className="eyebrow">ADMINISTRATION</p><h1>People & access</h1><p>Approve verified registrations and assign the only role the API will trust.</p></div><span>{users.length} accounts</span></div><div className="table-wrap"><table><thead><tr><th>Person</th><th>Database role</th><th>Identity</th><th>Access</th><th>Controls</th></tr></thead><tbody>{users.map((user) => { const emailReady = user.identity_provider === "microsoft" || Boolean(user.email_verified_at); return <tr key={user.id}><td><strong>{user.display_name}</strong><small>{user.email}</small></td><td><span className={`role-pill ${user.role}`}>{user.role}</span></td><td><span className={`access-status ${emailReady ? "approved" : "pending"}`}>{user.identity_provider === "microsoft" ? "Microsoft verified" : emailReady ? "Email verified" : "Email not verified"}</span></td><td><span className={`access-status ${user.is_active ? "approved" : "pending"}`}>{user.is_active ? "Approved" : "Pending / inactive"}</span></td><td className="controls"><select aria-label={`Role for ${user.display_name}`} value={user.role} onChange={(event) => void updateUser(user, { role: event.target.value as Role })}><option value="student">Student</option><option value="teacher">Teacher</option><option value="admin">Administrator</option></select><button className="quiet" disabled={!user.is_active && !emailReady} title={!emailReady ? "Email verification is required first" : ""} onClick={() => void updateUser(user, { is_active: !user.is_active })}>{user.is_active ? "Deactivate" : "Approve & activate"}</button></td></tr>; })}</tbody></table></div></section>}
        {currentUser.role === "admin" && view === "audit" && <section className="panel"><div className="section-heading"><div><p className="eyebrow">SECURITY</p><h1>Audit activity</h1><p>Registration requests and access changes are recorded here.</p></div><span>Latest {events.length}</span></div><div className="event-list">{events.map((event) => <article key={event.id}><span className={`outcome ${event.outcome}`} /><div><strong>{event.action.replaceAll(".", " ")}</strong><p>{new Date(event.occurred_at).toLocaleString()} · {event.target_type ?? "portal"}</p></div></article>)}</div></section>}
      </main>
    </div>
  );
}
