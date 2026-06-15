import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Source } from "./api";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  confidence?: number;
  timestamp: number;
}

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  addMessage: (message: ChatMessage) => void;
  updateLastMessage: (content: string) => void;
  setStreaming: (streaming: boolean) => void;
  clearMessages: () => void;
  newChat: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
      messages: [],
      isStreaming: false,

      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      updateLastMessage: (content) =>
        set((state) => {
          const messages = [...state.messages];
          if (messages.length > 0) {
            const last = { ...messages[messages.length - 1] };
            last.content = content;
            messages[messages.length - 1] = last;
          }
          return { messages };
        }),

      setStreaming: (streaming) => set({ isStreaming: streaming }),

      clearMessages: () => set({ messages: [] }),

      newChat: () => set({ messages: [] }),
    }),
    {
      name: "chat-history",
      partialize: (state) => ({
        messages: state.messages.slice(-100),
      }),
    },
  ),
);

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
