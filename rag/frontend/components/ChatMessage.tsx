"use client";

import { GraduationCap, User, Lightbulb, Pencil, Brain } from "lucide-react";
import { motion } from "framer-motion";
import { SourceCard } from "@/components/SourceCard";
import { VoicePlayback } from "@/components/VoicePlayback";
import { getConfidenceColor, getConfidenceLabel } from "@/lib/api";
import type { ChatMessage as ChatMessageType } from "@/lib/store";

interface ChatMessageProps {
  message: ChatMessageType;
}

function TeacherActionBadge({ action }: { action: string }) {
  const config: Record<string, { icon: React.ReactNode; label: string; color: string }> = {
    explain: { icon: <Lightbulb className="h-3 w-3" />, label: "Explaining", color: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300" },
    socratic_ask: { icon: <Brain className="h-3 w-3" />, label: "Think about it", color: "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300" },
    exercise: { icon: <Pencil className="h-3 w-3" />, label: "Exercise", color: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300" },
    check: { icon: <Brain className="h-3 w-3" />, label: "Check", color: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300" },
    encourage: { icon: <Lightbulb className="h-3 w-3" />, label: "Encouragement", color: "bg-pink-100 text-pink-700 dark:bg-pink-900 dark:text-pink-300" },
  };
  const c = config[action] || config.explain;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-medium ${c.color}`}>
      {c.icon}
      {c.label}
    </span>
  );
}

function MicroExerciseCard({ exercise }: { exercise: ChatMessageType["micro_exercise"] }) {
  if (!exercise) return null;
  const typeLabels: Record<string, string> = {
    fill_blank: "Fill in the blank",
    predict_output: "Predict the output",
    find_mistake: "Find the mistake",
    complete_query: "Complete the query",
    choose_clause: "Choose the correct clause",
  };
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 rounded-lg border-2 border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-4"
    >
      <div className="flex items-center gap-2 mb-2">
        <Pencil className="h-4 w-4 text-amber-600 dark:text-amber-400" />
        <span className="text-xs font-semibold text-amber-700 dark:text-amber-300 uppercase tracking-wider">
          {typeLabels[exercise.type] || "Exercise"}
        </span>
      </div>
      <p className="text-sm font-mono whitespace-pre-wrap">{exercise.question}</p>
      {exercise.hint && (
        <p className="text-xs text-muted-foreground mt-2 italic">💡 {exercise.hint}</p>
      )}
    </motion.div>
  );
}

function StudentPrompt({ text, type }: { text: string; type?: string }) {
  if (!text) return null;
  const icon = type === "exercise" ? <Pencil className="h-4 w-4" /> : <Brain className="h-4 w-4" />;
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 rounded-lg border border-dashed border-primary/40 bg-primary/5 p-3"
    >
      <div className="flex items-start gap-2">
        <div className="mt-0.5 text-primary">{icon}</div>
        <div>
          <p className="text-xs font-medium text-primary mb-1">
            {type === "exercise" ? "Try this:" : "Your turn:"}
          </p>
          <p className="text-sm">{text}</p>
        </div>
      </div>
    </motion.div>
  );
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
            : "bg-gradient-to-br from-blue-500 to-purple-600 text-white"
        }`}
      >
        {isUser ? <User className="h-4 w-4" /> : <GraduationCap className="h-4 w-4" />}
      </div>

      <div className={`max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        {!isUser && message.teacher_action && (
          <div className="mb-1.5 flex items-center gap-2">
            <TeacherActionBadge action={message.teacher_action} />
            {message.teaching_state?.difficulty && (
              <span className="text-[10px] text-muted-foreground">
                {message.teaching_state.difficulty}
              </span>
            )}
          </div>
        )}

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

          {!isUser && message.micro_exercise && (
            <MicroExerciseCard exercise={message.micro_exercise} />
          )}

          {!isUser && message.student_prompt && (
            <StudentPrompt text={message.student_prompt} type={message.student_prompt_type} />
          )}
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
