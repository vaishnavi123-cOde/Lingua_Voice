"use client";

import { useEffect, useRef } from "react";
import { GraduationCap } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Sidebar } from "@/components/Sidebar";
import { ChatMessage } from "@/components/ChatMessage";
import { ChatInput } from "@/components/ChatInput";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useChatStore, useThemeStore } from "@/lib/store";

export default function Home() {
  const { messages } = useChatStore();
  const { isDark } = useThemeStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDark]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [messages]);

  return (
    <div className="flex h-screen">
      <Sidebar />

      <div className="flex-1 flex flex-col">
        <header className="border-b bg-background px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GraduationCap className="h-5 w-5 text-primary" />
            <h1 className="font-semibold">AI SQL Teacher</h1>
          </div>
          <ThemeToggle />
        </header>

        <ScrollArea ref={scrollRef} className="flex-1 p-4">
          {messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md">
                <GraduationCap className="h-12 w-12 mx-auto text-primary mb-4" />
                <h2 className="text-xl font-semibold mb-2">
                  Welcome to AI SQL Teacher
                </h2>
                <p className="text-sm text-muted-foreground mb-6">
                  Your personal SQL instructor. Ask me anything about SQL, and I&apos;ll guide you step by step — just like a real teacher.
                </p>
                <div className="grid grid-cols-2 gap-3 text-left">
                  <div className="rounded-lg border p-3 text-sm hover:border-primary/50 cursor-pointer transition-colors">
                    <p className="font-medium mb-1">📊 Databases</p>
                    <p className="text-muted-foreground text-xs">
                      CREATE TABLE, data types, constraints
                    </p>
                  </div>
                  <div className="rounded-lg border p-3 text-sm hover:border-primary/50 cursor-pointer transition-colors">
                    <p className="font-medium mb-1">🔗 Relationships</p>
                    <p className="text-muted-foreground text-xs">
                      Foreign keys, JOINs, normalization
                    </p>
                  </div>
                  <div className="rounded-lg border p-3 text-sm hover:border-primary/50 cursor-pointer transition-colors">
                    <p className="font-medium mb-1">📝 Queries</p>
                    <p className="text-muted-foreground text-xs">
                      SELECT, WHERE, GROUP BY, filtering
                    </p>
                  </div>
                  <div className="rounded-lg border p-3 text-sm hover:border-primary/50 cursor-pointer transition-colors">
                    <p className="font-medium mb-1">🔧 Administration</p>
                    <p className="text-muted-foreground text-xs">
                      SSMS, SQLCMD, import/export
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-6 pb-4">
              {messages.map((message) => (
                <ChatMessage key={message.id} message={message} />
              ))}
            </div>
          )}
        </ScrollArea>

        <ChatInput />
      </div>
    </div>
  );
}
