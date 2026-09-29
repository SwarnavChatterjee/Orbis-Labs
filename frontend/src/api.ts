const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api").replace(/\/$/, "");
export const GOOGLE_LOGIN_URL = `${API_BASE}/auth/google/login`;

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
  stream.addEventListener("status", (event) => {
    try {
      onEvent(JSON.parse((event as MessageEvent).data));
    } catch {
      onError("The progress stream returned an invalid event.");
    }
  });
  stream.onerror = () => {
    if (stream.readyState === EventSource.CLOSED) onDone();
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
