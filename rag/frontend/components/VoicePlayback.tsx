"use client";

import { useState, useRef } from "react";
import { Play, Square, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { speakText } from "@/lib/api";

interface VoicePlaybackProps {
  text: string;
}

export function VoicePlayback({ text }: VoicePlaybackProps) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const handlePlay = async () => {
    if (isPlaying && audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
      return;
    }

    setError(null);
    setIsLoading(true);
    try {
      const blob = await speakText(text);
      const url = URL.createObjectURL(blob);

      if (audioRef.current) {
        audioRef.current.pause();
        URL.revokeObjectURL(audioRef.current.src);
      }

      const audio = new Audio(url);
      audioRef.current = audio;

      audio.onended = () => {
        setIsPlaying(false);
        URL.revokeObjectURL(url);
      };

      audio.onerror = () => {
        setIsPlaying(false);
        setError("Audio playback failed");
        URL.revokeObjectURL(url);
      };

      await audio.play();
      setIsPlaying(true);
    } catch (err) {
      console.error("TTS failed:", err);
      setError(err instanceof Error ? err.message : "TTS unavailable");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex items-center gap-1.5">
      <Button
        variant="ghost"
        size="sm"
        onClick={handlePlay}
        disabled={isLoading}
        title={isPlaying ? "Stop" : "Read aloud"}
        className="gap-1.5"
      >
        {isLoading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : isPlaying ? (
          <Square className="h-3.5 w-3.5" />
        ) : (
          <Play className="h-3.5 w-3.5" />
        )}
        <span className="text-xs">{isPlaying ? "Stop" : "Listen"}</span>
      </Button>
      {error && <span className="text-[10px] text-destructive">{error}</span>}
    </div>
  );
}
