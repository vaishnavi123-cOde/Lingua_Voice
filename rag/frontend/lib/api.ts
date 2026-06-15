const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Source {
  source: string;
  score: number;
  rank: number;
}

export interface AnswerResponse {
  question: string;
  answer: string;
  sources: Source[];
  confidence: number;
  retrieval_time_ms: number;
  llm_time_ms: number;
  total_time_ms: number;
}

export interface HealthResponse {
  status: string;
  version: string;
  qdrant_connected: boolean;
  ollama_connected: boolean;
  total_chunks: number;
  embeddings_loaded: boolean;
}

export async function askQuestion(question: string): Promise<AnswerResponse> {
  const url = `${API_BASE}/ask`;
  const payload = { question };
  console.log("Request URL:", url);
  console.log("Request Payload:", JSON.stringify(payload));
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  console.log("Response status:", res.status, res.statusText);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    console.log("Response error:", err);
    throw new Error(err.detail || "Failed to get answer");
  }
  const data = await res.json();
  console.log("Response data:", data);
  return data;
}

export async function askQuestionStream(
  question: string,
  onChunk: (text: string) => void,
  onSources?: (sources: Source[]) => void,
  onError?: (error: Error) => void,
): Promise<void> {
  try {
    const url = `${API_BASE}/ask/stream`;
    const payload = { question };
    console.log("Stream Request URL:", url);
    console.log("Stream Request Payload:", JSON.stringify(payload));
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    console.log("Stream Response status:", res.status, res.statusText);
    if (!res.ok) throw new Error("Stream request failed");

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No reader available");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const sourcesIdx = buffer.indexOf("__SOURCES__:");
      if (sourcesIdx !== -1) {
        onChunk(buffer.slice(0, sourcesIdx));
        const sourcesJson = buffer.slice(sourcesIdx + "__SOURCES__:".length);
        try {
          const parsed = JSON.parse(sourcesJson);
          onSources?.(parsed);
        } catch {
          // ignore parse errors
        }
        break;
      }
      onChunk(buffer);
      buffer = "";
    }
  } catch (err) {
    onError?.(err instanceof Error ? err : new Error(String(err)));
  }
}

export async function speakText(text: string): Promise<Blob> {
  const url = `${API_BASE}/speak`;
  const payload = { text };
  console.log("TTS Request URL:", url);
  console.log("TTS Request Payload:", JSON.stringify(payload));
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  console.log("TTS Response status:", res.status, res.statusText);
  if (!res.ok) {
    let detail = "TTS failed";
    try { const err = await res.json(); detail = err.detail || detail; } catch {}
    throw new Error(detail);
  }
  return res.blob();
}

export async function checkHealth(): Promise<HealthResponse> {
  const url = `${API_BASE}/health`;
  console.log("Health Request URL:", url);
  const res = await fetch(url);
  console.log("Health Response status:", res.status, res.statusText);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}

export function getConfidenceLabel(score: number): string {
  if (score >= 0.85) return "High";
  if (score >= 0.70) return "Medium";
  if (score >= 0.50) return "Low";
  return "Very Low";
}

export function getConfidenceColor(score: number): string {
  if (score >= 0.85) return "text-green-500";
  if (score >= 0.70) return "text-yellow-500";
  if (score >= 0.50) return "text-orange-500";
  return "text-red-500";
}
