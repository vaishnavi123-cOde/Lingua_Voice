"use client";

import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useThemeStore } from "@/lib/store";

export function ThemeToggle() {
  const { isDark, toggle } = useThemeStore();

  return (
    <Button variant="ghost" size="icon" onClick={toggle} title="Toggle theme">
      {isDark ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
    </Button>
  );
}
