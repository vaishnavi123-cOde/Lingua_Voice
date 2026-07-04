import { create } from "zustand";
import { persist } from "zustand/middleware";

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

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  confidence?: number;
  timestamp: number;
  teacher_action?: string;
  teaching_state?: TeachingState;
  student_prompt?: string;
  student_prompt_type?: string;
  micro_exercise?: MicroExercise;
  session_id?: string;
}

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  sessionId: string | null;
  teachingState: TeachingState | null;
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (content: string, extra?: Partial<ChatMessage>) => void;
  setStreaming: (streaming: boolean) => void;
  clearMessages: () => void;
  newChat: () => void;
  setSessionId: (id: string) => void;
  setTeachingState: (state: TeachingState | null) => void;
}

interface ThemeState {
  isDark: boolean;
  toggle: () => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      isDark: false,
      toggle: () =>
        set((state) => {
          const newDark = !state.isDark;
          if (typeof document !== "undefined") {
            document.documentElement.classList.toggle("dark", newDark);
          }
          return { isDark: newDark };
        }),
    }),
    { name: "theme-preference" },
  ),
);

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      isStreaming: false,
      sessionId: null,
      teachingState: null,

      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      updateLastMessage: (content, extra) =>
        set((state) => {
          const messages = [...state.messages];
          if (messages.length > 0) {
            const last = { ...messages[messages.length - 1], ...extra };
            last.content = content;
            messages[messages.length - 1] = last;
          }
          return { messages };
        }),

      setStreaming: (streaming) => set({ isStreaming: streaming }),

      clearMessages: () => set({ messages: [], teachingState: null, sessionId: null }),

      newChat: () => set({ messages: [], teachingState: null, sessionId: null }),

      setSessionId: (id) => set({ sessionId: id }),

      setTeachingState: (state) => set({ teachingState: state }),
    }),
    {
      name: "chat-history",
      partialize: (state) => ({
        messages: state.messages.slice(-100),
        sessionId: state.sessionId,
      }),
    },
  ),
);
