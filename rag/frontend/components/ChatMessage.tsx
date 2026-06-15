"use client";

import { Bot, User } from "lucide-react";
import { motion } from "framer-motion";
import { SourceCard } from "@/components/SourceCard";
import { VoicePlayback } from "@/components/VoicePlayback";
import { getConfidenceColor, getConfidenceLabel } from "@/lib/api";
import type { ChatMessage as ChatMessageType } from "@/lib/store";

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : ""}`}
    >
      <div
        className={`flex items-center justify-center w-8 h-8 rounded-full shrink-0 ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-muted-foreground"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className={`max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`rounded-lg px-4 py-3 ${
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted/50 border"
          }`}
        >
          <p className="text-sm whitespace-pre-wrap markdown-content">
            {message.content}
          </p>
        </div>

        {!isUser && message.content && (
          <div className="flex items-center gap-2 mt-2">
            <VoicePlayback text={message.content} />

            {message.confidence !== undefined && (
              <span
                className={`text-xs ${getConfidenceColor(message.confidence)}`}
              >
                {getConfidenceLabel(message.confidence)} confidence
                ({Math.round(message.confidence * 100)}%)
              </span>
            )}
          </div>
        )}

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-2 space-y-1.5">
            <p className="text-[11px] text-muted-foreground font-medium uppercase tracking-wider">
              Sources
            </p>
            {message.sources.map((source, i) => (
              <SourceCard key={i} source={source} />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}
