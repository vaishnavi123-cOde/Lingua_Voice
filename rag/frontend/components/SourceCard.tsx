"use client";

import { FileText } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { getConfidenceColor } from "@/lib/api";
import type { Source } from "@/lib/api";

interface SourceCardProps {
  source: Source;
}

export function SourceCard({ source }: SourceCardProps) {
  const scorePercent = Math.round(source.score * 100);
  const scoreColor = getConfidenceColor(source.score);

  return (
    <Card className="p-3 text-xs">
      <div className="flex items-start gap-2">
        <FileText className="h-3.5 w-3.5 mt-0.5 text-muted-foreground shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="font-medium truncate" title={source.source}>
            {source.source}
          </p>
          <div className="flex items-center gap-2 mt-1">
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
              Rank #{source.rank}
            </Badge>
            <span className={scoreColor}>
              {scorePercent}% match
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}
