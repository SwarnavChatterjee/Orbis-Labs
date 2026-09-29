const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api").replace(/\/$/, "");
export const GOOGLE_LOGIN_URL = `${API_BASE}/auth/google/login`;
export const FRONTEND_DEMO_MODE = import.meta.env.VITE_DEMO_MODE === "true";

export type QueryStatus = "queued" | "running" | "planned" | "collecting" | "cleaning" | "completed" | "failed";

export type QueryHistoryItem = {
  id: string;
  raw_text: string;
  status: QueryStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
};

export type QueryResult = {
  id: string;
  company: string;
  role: string;
  location: string | null;
  source_url: string;
  source_name: string | null;
  retrieved_at: string;
  confidence: number | null;
  validation_errors: string[];
};

export type AuthUser = { id: string; email: string; display_name: string | null; avatar_url: string | null };

export const DEMO_USER: AuthUser = {
  id: "demo-user",
  email: "demo@orbis-labs.local",
  display_name: "Orbis Demo",
  avatar_url: null,
};

export function getDemoResults(rawText: string): QueryResult[] {
  const retrievedAt = new Date().toISOString();
  return [
    { id: `demo-${rawText.length}-1`, company: "Northstar Labs", role: "Product Design Intern", location: "Bengaluru, India", source_url: "https://demo.orbis-labs.local/internshala/northstar-product-design", source_name: "Internshala", retrieved_at: retrievedAt, confidence: 0.96, validation_errors: [] },
    { id: `demo-${rawText.length}-2`, company: "GitLab", role: "Associate Product Designer", location: "Remote", source_url: "https://demo.orbis-labs.local/greenhouse/gitlab-associate-product-designer", source_name: "GitLab Greenhouse", retrieved_at: retrievedAt, confidence: 0.93, validation_errors: [] },
    { id: `demo-${rawText.length}-3`, company: "Mosaic Digital", role: "UX Research Intern", location: "Hyderabad, India", source_url: "https://demo.orbis-labs.local/internshala/mosaic-ux-research", source_name: "Internshala", retrieved_at: retrievedAt, confidence: 0.89, validation_errors: [] },
    { id: `demo-${rawText.length}-4`, company: "Orbit Analytics", role: "Data Analyst Intern", location: "Remote", source_url: "https://demo.orbis-labs.local/greenhouse/orbit-data-analyst", source_name: "GitLab Greenhouse", retrieved_at: retrievedAt, confidence: 0.86, validation_errors: [] },
    { id: `demo-${rawText.length}-5`, company: "Kindred Commerce", role: "Visual Design Intern", location: "Mumbai, India", source_url: "https://demo.orbis-labs.local/internshala/kindred-visual-design", source_name: "Internshala", retrieved_at: retrievedAt, confidence: 0.82, validation_errors: [] },
  ];
}

type Envelope<T> = { success: true; data: T } | { success: false; error: string };

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
  });
  const body = (await response.json()) as Envelope<T>;
  if (!response.ok || !body.success) throw new Error(body.success ? "Request failed" : body.error);
  return body.data;
}

export function submitQuery(rawText: string) {
  return request<{ query_id: string }>("/queries", { method: "POST", body: JSON.stringify({ raw_text: rawText }) });
}

export function getCurrentUser() {
  return request<AuthUser>("/auth/me");
}

export function logout() {
  return request<{ success: true }>("/auth/logout", { method: "POST" });
}

export function getQuery(queryId: string) {
  return request<{ id: string; raw_text: string; status: QueryStatus; error_message: string | null; record_count: number }>(`/queries/${queryId}`);
}

export function getHistory() {
  return request<{ items: QueryHistoryItem[]; total: number }>("/queries?page=1&page_size=20");
}

export function getResults(queryId: string, filters: { location?: string; role?: string; minConfidence?: string }) {
  const params = new URLSearchParams({ page: "1", page_size: "100" });
  if (filters.location) params.set("location", filters.location);
  if (filters.role) params.set("role", filters.role);
  if (filters.minConfidence) params.set("min_confidence", filters.minConfidence);
  return request<{ items: QueryResult[]; total: number }>(`/queries/${queryId}/results?${params}`);
}

export function rerunQuery(queryId: string) {
  return request<{ query_id: string }>(`/queries/${queryId}/rerun`, { method: "POST" });
}

export function streamQuery(queryId: string, onEvent: (event: { status: QueryStatus; message: string | null }) => void, onDone: () => void, onError: (error: string) => void) {
  const stream = new EventSource(`${API_BASE}/queries/${queryId}/stream`, { withCredentials: true });
  let terminal = false;
  stream.addEventListener("status", (event) => {
    try {
      const payload = JSON.parse((event as MessageEvent).data) as { status: QueryStatus; message: string | null };
      onEvent(payload);
      if (payload.status === "completed" || payload.status === "failed") {
        terminal = true;
        stream.close();
        onDone();
      }
    } catch {
      onError("The progress stream returned an invalid event.");
    }
  });
  stream.onerror = () => {
    if (terminal || stream.readyState === EventSource.CLOSED) onDone();
    else onError("The progress stream disconnected.");
    stream.close();
  };
  return () => stream.close();
}

export function downloadCsv(rows: QueryResult[]) {
  const header = ["Company", "Role", "Location", "Source", "Confidence", "Source URL"];
  const values = rows.map((row) => [row.company, row.role, row.location ?? "", row.source_name ?? "", row.confidence?.toFixed(2) ?? "", row.source_url]);
  const csv = [header, ...values].map((row) => row.map((value) => `"${String(value).replace(/"/g, '""')}"`).join(",")).join("\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  link.download = "orbis-results.csv";
  link.click();
  URL.revokeObjectURL(link.href);
}
