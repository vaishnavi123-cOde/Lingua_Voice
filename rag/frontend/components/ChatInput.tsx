"use client";

import { useState, useRef, useEffect, useCallback, type KeyboardEvent } from "react";
import { Send, Loader2, Mic, MicOff } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useChatStore } from "@/lib/store";
import { askQuestion } from "@/lib/api";

declare global {
  interface Window {
    SpeechRecognition: any;
    webkitSpeechRecognition: any;
  }
}

export function ChatInput() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);
  const {
    addMessage,
    updateLastMessage,
    sessionId,
    teachingState,
    setSessionId,
    setTeachingState,
  } = useChatStore();

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSubmit = async () => {
    const question = input.trim();
    if (!question || isLoading) return;

    setInput("");
    setIsLoading(true);

    addMessage({
      id: Date.now().toString(),
      role: "user",
      content: question,
      timestamp: Date.now(),
    });

    const assistantId = (Date.now() + 1).toString();
    addMessage({
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    });

    try {
      const response = await askQuestion(question, sessionId, teachingState);

      if (response.session_id && !sessionId) {
        setSessionId(response.session_id);
      }
      if (response.teaching_state) {
        setTeachingState(response.teaching_state);
      }

      const extra: Record<string, unknown> = {};
      if (response.sources) extra.sources = response.sources;
      if (response.confidence !== undefined) extra.confidence = response.confidence;
      if (response.teacher_action) extra.teacher_action = response.teacher_action;
      if (response.teaching_state) extra.teaching_state = response.teaching_state;
      if (response.student_prompt) extra.student_prompt = response.student_prompt;
      if (response.student_prompt_type) extra.student_prompt_type = response.student_prompt_type;
      if (response.micro_exercise) extra.micro_exercise = response.micro_exercise;
      if (response.session_id) extra.session_id = response.session_id;

      updateLastMessage(response.answer, extra);

      const message = useChatStore.getState().messages;
      const updated = [...message];
      const lastIdx = updated.length - 1;
      if (lastIdx >= 0) {
        updated[lastIdx] = {
          ...updated[lastIdx],
          ...extra,
        };
        useChatStore.setState({ messages: updated });
      }
    } catch (err) {
      updateLastMessage(
        "Sorry, I encountered an error. Please try again."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const toggleRecording = useCallback(() => {
    if (isRecording) {
      recognitionRef.current?.stop();
      setIsRecording(false);
      return;
    }

    const SpeechRecognitionAPI =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognitionAPI) {
      console.warn("Speech Recognition not supported in this browser");
      return;
    }

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInput(transcript);
      setIsRecording(false);
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error:", event.error);
      setIsRecording(false);
    };

    recognition.onend = () => {
      setIsRecording(false);
    };

    recognitionRef.current = recognition;
    recognition.start();
    setIsRecording(true);
  }, [isRecording]);

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t bg-background p-4">
      <div className="max-w-3xl mx-auto flex gap-2">
        <Input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask your SQL teacher..."
          disabled={isLoading}
          className="flex-1"
        />
        <Button
          onClick={toggleRecording}
          disabled={isLoading}
          size="icon"
          variant={isRecording ? "destructive" : "outline"}
          title={isRecording ? "Tap to stop recording" : "Tap to speak"}
        >
          {isRecording ? (
            <MicOff className="h-4 w-4" />
          ) : (
            <Mic className="h-4 w-4" />
          )}
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={!input.trim() || isLoading}
          size="icon"
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Send className="h-4 w-4" />
          )}
        </Button>
      </div>
    </div>
  );
}
