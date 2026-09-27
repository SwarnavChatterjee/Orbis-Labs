import { FormEvent, useState } from "react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const examples = [
  "Software engineering internships in India",
  "Remote product roles for early-career talent",
  "Climate tech companies hiring in Bengaluru",
];

function ArrowUpRight() {
  return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="M5 15 15 5M7 5h8v8" /></svg>;
}

function Spark() {
  return <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z" /><path d="m19 16 .8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16Z" /></svg>;
}

function Check() {
  return <svg viewBox="0 0 20 20" aria-hidden="true"><path d="m4 10 4 4 8-8" /></svg>;
}

function App() {
  const [query, setQuery] = useState("");
  const [submitted, setSubmitted] = useState(false);

  function submitQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (query.trim()) setSubmitted(true);
  }

  return (
    <div className="page-shell">
      <div className="ambient ambient-one" /><div className="ambient ambient-two" />
      <header className="nav wrap">
        <a className="brand" href="#top" aria-label="Orbis Labs home"><span className="brand-mark"><span /></span><span>Orbis <em>Labs</em></span></a>
        <nav className="nav-links" aria-label="Primary navigation"><a href="#how-it-works">How it works</a><a href="#principles">Why Orbis</a><a href="#about">About</a></nav>
        <a className="nav-cta" href="#start">Start exploring <ArrowUpRight /></a>
      </header>

      <main id="top">
        <section className="hero wrap">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-dot" /> Intelligence for the real world</div>
            <h1>Ask for the data.<br /><span>Get the signal.</span></h1>
            <p className="hero-intro">Orbis Labs turns plain-language questions into clean, source-backed datasets—so you can move from curiosity to confident action.</p>
            <form className="query-composer" id="start" onSubmit={submitQuery}>
              <div className="composer-top"><Spark /><textarea aria-label="Describe the data you need" value={query} onChange={(event) => { setQuery(event.target.value); setSubmitted(false); }} placeholder="Tell us what you want to find..." rows={2} /></div>
              <div className="composer-bottom"><span className="composer-hint">No prompt engineering required.</span><button className="primary-button" type="submit">{submitted ? "Request received" : "Start collection"}<ArrowUpRight /></button></div>
            </form>
            <div className="suggestions" aria-label="Example queries"><span>Try an example</span>{examples.map((example) => <button key={example} type="button" onClick={() => setQuery(example)}>{example}</button>)}</div>
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
            <article><div className="number">03</div><h3>Built for momentum.</h3><p>Go from “I wonder” to “we know” in minutes. Export, share, and make the next decision with confidence.</p><a href="#start">Start a collection <ArrowUpRight /></a></article>
          </div>
        </section>

        <section className="workflow wrap" id="how-it-works">
          <div className="workflow-panel"><div className="eyebrow"><span className="eyebrow-dot" /> From question to clarity</div><h2>A better way to<br /><span>find what matters.</span></h2><p>Orbis combines the flexibility of AI with the discipline of data engineering. Your question is just the beginning.</p><a className="text-link" href="#start">See it in action <ArrowUpRight /></a></div>
          <div className="workflow-steps"><div><span>01</span><div><h3>Describe</h3><p>Say what you need in your own words. Orbis understands the intent behind the question.</p></div></div><div><span>02</span><div><h3>Discover</h3><p>We collect from permitted sources and show you exactly where every record came from.</p></div></div><div><span>03</span><div><h3>Decide</h3><p>Search, filter, validate, and export a dataset ready for the work ahead.</p></div></div></div>
        </section>

        <section className="closing wrap" id="about"><div className="closing-mark"><Spark /></div><p className="eyebrow">The next insight is closer than you think</p><h2>Start with a question.</h2><a className="primary-button" href="#start">Build your first dataset <ArrowUpRight /></a></section>
      </main>
      <footer className="footer wrap"><a className="brand" href="#top"><span className="brand-mark"><span /></span><span>Orbis <em>Labs</em></span></a><span>AI-powered data intelligence for the curious and the decisive.</span><span>© 2026 Orbis Labs</span></footer>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);

