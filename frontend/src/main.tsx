import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

function App() {
  return (
    <main className="shell">
      <p className="eyebrow">Orbis Labs</p>
      <h1>Source-backed intelligence for better decisions.</h1>
      <p className="intro">
        Describe the internships or jobs you need. Orbis Labs will collect,
        validate, and organize source-attributed records.
      </p>
      <div className="query-card">
        <textarea placeholder="Find software engineering internships in India..." />
        <button type="button">Start collection</button>
      </div>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
