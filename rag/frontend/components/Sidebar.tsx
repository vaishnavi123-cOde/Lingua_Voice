"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/lib/store";

export function Sidebar() {
  const { messages, newChat, clearMessages } = useChatStore();

  const chatCount = messages.filter((m) => m.role === "user").length;

  return (
    <div className="w-64 h-screen border-r bg-muted/30 flex flex-col p-4 hidden md:flex">
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-semibold text-lg">Chats</h2>
      </div>

      <Button
        onClick={newChat}
        className="w-full justify-start gap-2 mb-4"
        variant="outline"
      >
        <Plus className="h-4 w-4" />
        New Chat
      </Button>

      <div className="text-xs text-muted-foreground mb-2">
        {chatCount} question{chatCount !== 1 ? "s" : ""} asked
      </div>

      {messages.length > 0 && (
        <Button
          onClick={clearMessages}
          variant="ghost"
          size="sm"
          className="w-full justify-start gap-2 text-destructive hover:text-destructive"
        >
          <Trash2 className="h-4 w-4" />
          Clear All
        </Button>
      )}

      <div className="mt-auto text-xs text-muted-foreground">
        <p>AI SQL Teacher</p>
        <p>v2.0.0</p>
      </div>
    </div>
  );
}
