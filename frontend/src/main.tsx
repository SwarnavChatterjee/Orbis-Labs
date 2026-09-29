import { FormEvent, useEffect, useState } from "react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";
import { downloadCsv, getCurrentUser, getHistory, getQuery, getResults, GOOGLE_LOGIN_URL, QueryHistoryItem, QueryResult, QueryStatus, rerunQuery, streamQuery, submitQuery } from "./api";
import { logout } from "./api";

function ArrowUpRight() {
  return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 15 15 5M7 5h8v8" /></svg>;
}

function Spark() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z" /><path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z" /></svg>;
}

function Check() {
  return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m4 10 4 4 8-8" /></svg>;
}

function ProfileAvatar({ email, avatarUrl }: { email: string; avatarUrl: string | null }) {
  const [imageFailed, setImageFailed] = useState(false);
  const initials = email.slice(0, 2).toUpperCase();
  return avatarUrl && !imageFailed
    ? <img className="avatar avatar-image" src={avatarUrl} alt="Google profile" onError={() => setImageFailed(true)} />
    : <span className="avatar" aria-label="Profile initials">{initials}</span>;
}

const suggestedQueries = [
  "Software engineering internships in India",
  "Remote data analyst jobs for early-career talent",
  "Product design internships in Bengaluru",
];

function LandingPage() {
  return (
    <div className="page-shell">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <header className="nav wrap">
        <a className="brand" href="#top" aria-label="Orbis Labs home"><span className="brand-mark"><span /></span><span>Orbis <em>Labs</em></span></a>
        <nav className="nav-links" aria-label="Primary navigation"><a href="#how-it-works">How it works</a><a href="#principles">Why Orbis</a><a href="#about">About</a></nav>
        <a className="google-button" href={GOOGLE_LOGIN_URL} aria-label="Sign in with Google"><img src="/google-signin.svg" alt="Sign in with Google" /></a>
      </header>

      <main id="top">
        <section className="hero wrap">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-dot" /> Intelligence for the real world</div>
            <h1>Ask for the data.<br /><span>Get the signal.</span></h1>
            <p className="hero-intro">Orbis Labs turns plain-language questions into clean, source-backed datasets—so you can move from curiosity to confident action.</p>
            <a className="google-button hero-cta" href={GOOGLE_LOGIN_URL} aria-label="Sign in with Google"><img src="/google-signin.svg" alt="Sign in with Google" /></a>
          </div>

          <div className="hero-visual" aria-label="Orbis Labs collection preview">
            <div className="visual-glow" /><div className="orbit orbit-large" /><div className="orbit orbit-small" />
            <div className="signal-card main-card">
              <div className="card-heading"><div><span className="live-dot" /> Live collection</div><span className="card-menu">•••</span></div>
              <div className="collection-query">Software engineering<br /><strong>internships in India</strong></div>
              <div className="progress-line"><span /></div><div className="progress-meta"><span>Building your dataset</span><strong>72%</strong></div>
              <div className="pipeline">
                <div className="pipeline-step done"><span><Check /></span><div><strong>Understand</strong><small>Query structured</small></div></div>
                <div className="pipeline-step active"><span><Spark /></span><div><strong>Collect</strong><small>Scanning permitted sources</small></div></div>
                <div className="pipeline-step"><span>3</span><div><strong>Deliver</strong><small>Clean, traceable results</small></div></div>
              </div>
            </div>
            <div className="floating-card source-card"><span className="mini-icon">◎</span><div><small>Source verified</small><strong>Internshala</strong></div><Check /></div>
            <div className="floating-card count-card"><strong>248</strong><span>records found</span><i>↗ 18.4%</i></div>
          </div>
        </section>

        <section className="trust-row wrap" aria-label="Orbis Labs principles"><span>Built for people who need to know</span><div><b>01</b> Source-first</div><div><b>02</b> Structured by design</div><div><b>03</b> Ready to act</div></section>

        <section className="principles wrap" id="principles">
          <div className="section-intro"><div className="eyebrow"><span className="eyebrow-dot" /> The Orbis approach</div><h2>Less noise.<br /><span>More knowing.</span></h2></div>
          <div className="principle-grid">
            <article><div className="number">01</div><h3>Source-first, always.</h3><p>Every record traces back to where it came from and when it was retrieved. No black-box lists. No made-up answers.</p><a href="#how-it-works">See our approach <ArrowUpRight /></a></article>
            <article><div className="number">02</div><h3>Structured by design.</h3><p>Messy, natural-language questions become clean, searchable datasets that your team can actually use.</p><a href="#how-it-works">Explore the workflow <ArrowUpRight /></a></article>
            <article><div className="number">03</div><h3>Built for momentum.</h3><p>Go from “I wonder” to “we know” in minutes. Export, share, and make the next decision with confidence.</p><a href={GOOGLE_LOGIN_URL}>Start a collection <ArrowUpRight /></a></article>
          </div>
        </section>

        <section className="workflow wrap" id="how-it-works">
          <div className="workflow-panel"><div className="eyebrow"><span className="eyebrow-dot" /> From question to clarity</div><h2>A better way to<br /><span>find what matters.</span></h2><p>Orbis combines the flexibility of AI with the discipline of data engineering. Your question is just the beginning.</p><a className="text-link" href={GOOGLE_LOGIN_URL}>See it in action <ArrowUpRight /></a></div>
          <div className="workflow-steps"><div><span>01</span><div><h3>Describe</h3><p>Say what you need in your own words. Orbis understands the intent behind the question.</p></div></div><div><span>02</span><div><h3>Discover</h3><p>We collect from permitted sources and show you exactly where every record came from.</p></div></div><div><span>03</span><div><h3>Decide</h3><p>Search, filter, validate, and export a dataset ready for the work ahead.</p></div></div></div>
        </section>

        <section className="closing wrap" id="about"><div className="closing-mark"><Spark /></div><p className="eyebrow">The next insight is closer than you think</p><h2>Start with a question.</h2><a className="primary-button" href={GOOGLE_LOGIN_URL}>Build your first dataset <ArrowUpRight /></a></section>
      </main>
      <footer className="footer wrap"><a className="brand" href="#top"><span className="brand-mark"><span /></span><span>Orbis <em>Labs</em></span></a><span>AI-powered data intelligence for the curious and the decisive.</span><span>© 2026 Orbis Labs</span></footer>
    </div>
  );
}

function WorkspacePage() {
  const params = new URLSearchParams(window.location.search);
  const [query, setQuery] = useState(params.get("query") ?? "");
  const [activeQuery, setActiveQuery] = useState("");
  const [queryId, setQueryId] = useState<string | null>(null);
  const [status, setStatus] = useState<QueryStatus | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [results, setResults] = useState<QueryResult[]>([]);
  const [history, setHistory] = useState<QueryHistoryItem[]>([]);
  const [locationFilter, setLocationFilter] = useState("");
  const [roleFilter, setRoleFilter] = useState("");
  const [confidenceFilter, setConfidenceFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authLoading, setAuthLoading] = useState(true);
  const [user, setUser] = useState<{ email: string; avatar_url: string | null } | null>(null);
  const [profileOpen, setProfileOpen] = useState(false);

  useEffect(() => {
    getCurrentUser()
      .then((currentUser) => setUser(currentUser))
      .catch(() => setUser(null))
      .finally(() => setAuthLoading(false));
  }, []);

  useEffect(() => {
    if (!user) return;
    getHistory().then((data) => setHistory(data.items)).catch(() => undefined);
  }, [user]);

  async function signOut() {
    await logout().catch(() => undefined);
    window.location.href = "/";
  }

  useEffect(() => {
    if (!queryId) return;
    return streamQuery(
      queryId,
      (event) => {
        setStatus(event.status);
        setStatusMessage(event.message);
        if (event.status === "completed" || event.status === "failed") {
          getResults(queryId, { location: locationFilter, role: roleFilter, minConfidence: confidenceFilter })
            .then((data) => setResults(data.items))
            .catch((reason: Error) => setError(reason.message));
          getHistory().then((data) => setHistory(data.items)).catch(() => undefined);
        }
      },
      () => undefined,
      (reason) => setError(reason),
    );
  }, [queryId]);

  async function loadQuery(item: QueryHistoryItem) {
    setError(null);
    setQuery(item.raw_text);
    setActiveQuery(item.raw_text);
    setQueryId(item.id);
    setStatus(item.status);
    try {
      const details = await getQuery(item.id);
      setStatus(details.status);
      const data = await getResults(item.id, { location: locationFilter, role: roleFilter, minConfidence: confidenceFilter });
      setResults(data.items);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load this query.");
    }
  }

  async function runWorkspaceQuery() {
    if (loading) return;
    if (!query.trim()) {
      setError("Describe what you want Orbis to collect before starting.");
      return;
    }
    setLoading(true);
    setError(null);
    setResults([]);
    try {
      const accepted = await submitQuery(query.trim());
      setQueryId(accepted.query_id);
      setActiveQuery(query.trim());
      setStatus("queued");
      setStatusMessage("Your collection has been queued.");
      getHistory().then((data) => setHistory(data.items)).catch(() => undefined);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to submit this query.");
    } finally {
      setLoading(false);
    }
  }

  function submitWorkspaceQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runWorkspaceQuery();
  }

  async function applyFilters() {
    if (!queryId) return;
    try {
      const data = await getResults(queryId, { location: locationFilter, role: roleFilter, minConfidence: confidenceFilter });
      setResults(data.items);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to filter these results.");
    }
  }

  async function startRerun() {
    if (!queryId) return;
    setError(null);
    try {
      const accepted = await rerunQuery(queryId);
      setQueryId(accepted.query_id);
      setStatus("queued");
      setStatusMessage("A fresh collection has been queued.");
      setResults([]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to rerun this query.");
    }
  }

  return (
    <div className="workspace-shell">
      <header className="workspace-nav">
        <a className="brand" href="/" aria-label="Return to Orbis Labs home"><span className="brand-mark"><span /></span><span>Orbis <em>Labs</em></span></a>
        <div className="workspace-nav-right">{user ? <><span className="workspace-status"><span /> {user.email}</span><div className="profile-control"><button className="profile-trigger" type="button" aria-label="Open profile menu" aria-expanded={profileOpen} onClick={() => setProfileOpen((open) => !open)}><ProfileAvatar email={user.email} avatarUrl={user.avatar_url} /><span className={`profile-chevron ${profileOpen ? "open" : ""}`}>⌄</span></button>{profileOpen && <div className="profile-menu"><div className="profile-menu-identity"><ProfileAvatar email={user.email} avatarUrl={user.avatar_url} /><div><strong>{user.email}</strong><small>Google account</small></div></div><button className="logout-button" type="button" onClick={signOut}>Log out</button></div>}</div></> : <span className="workspace-status"><span className="error-dot" /> Authentication required</span>}</div>
      </header>
      <div className="workspace-layout">
        <aside className="workspace-sidebar">
          <button className="new-query" type="button" onClick={() => { setQuery(""); setActiveQuery(""); setQueryId(null); setStatus(null); setResults([]); setError(null); }}><span>+</span> New collection</button>
          <div className="sidebar-label">Workspace</div>
          <a className="sidebar-link active" href="/app"><span>⌕</span> Explore data</a>
          <a className="sidebar-link" href="#history"><span>◷</span> Query history</a>
          <div className="sidebar-label history-label">Recent queries</div>
          {history.length === 0 ? <div className="history-empty">No collections yet.</div> : history.slice(0, 5).map((item) => <button className="recent-query recent-query-button" key={item.id} type="button" onClick={() => loadQuery(item)}><span className={`recent-dot ${item.status === "completed" ? "completed" : ""}`} /><div><strong>{item.raw_text}</strong><small>{item.status}</small></div></button>)}
          <div className="sidebar-footer"><div className="sidebar-card"><Spark /><div><strong>Source-backed by design</strong><small>Every record has a trail.</small></div></div><a className="sidebar-link" href="/"><span>←</span> Back to home</a></div>
        </aside>
        <main className="workspace-main">
          {authLoading ? <section className="auth-gate"><div className="empty-orb"><Spark /></div><h1>Checking your access…</h1><p>Orbis is verifying your Google session.</p></section> : !user ? <section className="auth-gate"><div className="empty-orb"><Spark /></div><div className="eyebrow"><span className="eyebrow-dot" /> Private workspace</div><h1>Sign in from the landing page.</h1><p>Return to the Orbis Labs landing page and use the Google sign-in button to enter this workspace.</p><a className="primary-button" href="/">Back to landing page <ArrowUpRight /></a></section> : <>
          <div className="workspace-heading"><div><div className="eyebrow"><span className="eyebrow-dot" /> Orbis workspace</div><h1>What are you looking for?</h1><p>Describe the dataset you need. Orbis will structure, search, and organize the signal.</p></div><div className="workspace-badge"><Spark /><span>AI-assisted<br /><strong>data discovery</strong></span></div></div>
          <form className="workspace-composer" onSubmit={submitWorkspaceQuery}>
            <div className="workspace-composer-top"><Spark /><textarea aria-label="Search for data" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. Find software engineering internships in India for 2027 graduates..." rows={3} /></div>
            <div className="workspace-composer-bottom"><div className="filter-pills"><input aria-label="Filter by role" value={roleFilter} onChange={(event) => setRoleFilter(event.target.value)} placeholder="Role" /><input aria-label="Filter by location" value={locationFilter} onChange={(event) => setLocationFilter(event.target.value)} placeholder="Location" /><select aria-label="Minimum confidence" value={confidenceFilter} onChange={(event) => setConfidenceFilter(event.target.value)}><option value="">Any confidence</option><option value="0.8">80%+</option><option value="0.9">90%+</option></select>{queryId && <button className="filter-apply" type="button" onClick={applyFilters}>Apply filters</button>}</div><button className="primary-button" type="button" onClick={() => void runWorkspaceQuery()} disabled={loading}>{loading ? "Submitting…" : activeQuery ? "Run again" : "Start collection"}<ArrowUpRight /></button></div>
          </form>
          <div className="suggested-queries" aria-label="Suggested example queries"><span>Try a suggestion</span>{suggestedQueries.map((suggestion) => <button key={suggestion} type="button" onClick={() => setQuery(suggestion)}>{suggestion}</button>)}</div>
          {error && !activeQuery && <div className="workspace-error">{error}</div>}
          {activeQuery ? <><section className="workspace-active"><div className="active-header"><div><span className={`live-dot ${status === "failed" ? "error-dot" : ""}`} /> {status ?? "queued"}</div><span>{statusMessage ?? "Collection in progress"}</span></div><h2>{activeQuery}</h2><div className="active-grid"><div><small>Query status</small><strong>{status ?? "queued"}</strong></div><div><small>Sources</small><strong>Internshala + GitLab</strong></div><div><small>Records</small><strong>{results.length}</strong></div></div><div className="active-actions"><button className="text-link" type="button" onClick={() => setActiveQuery("")}>Edit query <ArrowUpRight /></button><button className="text-link" type="button" onClick={startRerun}>Rerun <ArrowUpRight /></button></div></section>{error && <div className="workspace-error">{error}</div>}{status === "completed" && <section className="results-panel"><div className="results-heading"><div><div className="eyebrow"><span className="eyebrow-dot" /> Collection results</div><h2>{results.length} records found</h2></div><button className="export-button" type="button" onClick={() => downloadCsv(results)} disabled={!results.length}>Export CSV <ArrowUpRight /></button></div>{results.length ? <div className="results-table-wrap"><table className="results-table"><thead><tr><th>Role</th><th>Company</th><th>Location</th><th>Source</th><th>Confidence</th></tr></thead><tbody>{results.map((result) => <tr key={result.id}><td><strong>{result.role}</strong><a href={result.source_url} target="_blank" rel="noreferrer">View source ↗</a></td><td>{result.company}</td><td>{result.location ?? "—"}</td><td><span className="source-tag">{result.source_name ?? "Unknown"}</span></td><td>{result.confidence == null ? "—" : `${Math.round(result.confidence * 100)}%`}</td></tr>)}</tbody></table></div> : <div className="results-empty">No records matched this query or its filters.</div>}</section>}</> : <section className="workspace-empty"><div className="empty-orb"><Spark /></div><h2>Your next dataset starts here.</h2><p>Ask a question above to begin a source-backed collection. You’ll see progress, provenance, and results in this workspace.</p><div className="empty-features"><span><Check /> Source verified</span><span><Check /> Structured output</span><span><Check /> Export ready</span></div></section>}
          </>}
        </main>
      </div>
    </div>
  );
}

function App() {
  return window.location.pathname.startsWith("/app") ? <WorkspacePage /> : <LandingPage />;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
