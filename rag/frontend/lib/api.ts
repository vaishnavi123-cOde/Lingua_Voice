const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Source {
  source: string;
  score: number;
  rank: number;
}

export interface MicroExercise {
  type: string;
  question: string;
  answer?: string;
  hint?: string;
}

export interface TeachingState {
  concept: string;
  difficulty: string;
  lesson_progress: string[];
  struggled_concepts: string[];
  examples_used: string[];
  pedagogical_goal: string;
}

export interface AnswerResponse {
  question: string;
  answer: string;
  sources: Source[];
  confidence: number;
  retrieval_time_ms: number;
  llm_time_ms: number;
  total_time_ms: number;
  teacher_action: string;
  teaching_state: TeachingState | null;
  student_prompt: string | null;
  student_prompt_type: string | null;
  micro_exercise: MicroExercise | null;
  session_id: string | null;
}

export interface HealthResponse {
  status: string;
  version: string;
  qdrant_connected: boolean;
  ollama_connected: boolean;
  total_chunks: number;
  embeddings_loaded: boolean;
}

export async function askQuestion(
  question: string,
  sessionId?: string | null,
  teachingState?: TeachingState | null,
): Promise<AnswerResponse> {
  const url = `${API_BASE}/ask`;
  const payload: Record<string, unknown> = { question };
  if (sessionId) payload.session_id = sessionId;
  if (teachingState) payload.teaching_state = teachingState;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Failed to get answer");
  }
  return res.json();
}

export async function askQuestionStream(
  question: string,
  onChunk: (text: string) => void,
  onMeta?: (meta: Record<string, unknown>) => void,
  onError?: (error: Error) => void,
  sessionId?: string | null,
  teachingState?: TeachingState | null,
): Promise<void> {
  try {
    const url = `${API_BASE}/ask/stream`;
    const payload: Record<string, unknown> = { question };
    if (sessionId) payload.session_id = sessionId;
    if (teachingState) payload.teaching_state = teachingState;
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Stream request failed");

    const reader = res.body?.getReader();
    if (!reader) throw new Error("No reader available");

    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const metaIdx = buffer.indexOf("__META__:");
      if (metaIdx !== -1) {
        onChunk(buffer.slice(0, metaIdx));
        const metaJson = buffer.slice(metaIdx + "__META__:".length);
        try {
          const parsed = JSON.parse(metaJson);
          onMeta?.(parsed);
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
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    let detail = "TTS failed";
    try { const err = await res.json(); detail = err.detail || detail; } catch {}
    throw new Error(detail);
  }
  return res.blob();
}

export async function checkHealth(): Promise<HealthResponse> {
  const url = `${API_BASE}/health`;
  const res = await fetch(url);
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
