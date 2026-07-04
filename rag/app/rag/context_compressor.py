import logging
import re

from app.models.retrieval_result import RetrievalResult

logger = logging.getLogger(__name__)


# Aggressive OCR noise patterns — remove everything that isn't lecture content
NOISE_PATTERNS = [
    # Windows file paths
    r"C:\\Users\\[^\\]+\\[^\n]{3,100}",
    r"D:\\[^\n]{3,100}",
    r"[A-Z]:\\[^\n]{3,100}",
    # Malformed paths (space instead of colon)
    r"C\s+/Users/[^/\n]+/[^\n]{3,100}",
    r"C\s+\\Users\\[^\\]+\\[^\n]{3,100}",
    # Windows paths with forward slashes
    r"C:/Users/[^/\n]+/[^\n]{3,100}",
    # AppData / INetCache
    r"AppData[^\n]{3,100}",
    r"INetCache[^\n]{3,100}",
    r"Content\.Outlook[^\n]{3,100}",
    # Meeting recording artifacts
    r"Meeting Recording[^\n]*",
    r"Recorded by[^\n]*",
    r"Organized by[^\n]*",
    r"Microsoft\s*Teams[^\n]*",
    r"Presented by[^\n]*",
    # Chat overlays
    r"Type\s*a\s*message[^\n]*",
    r"^\s*Chat\s*$",
    r"Ask\s*Copilot[^\n]*",
    r"Try\s*the\s*new\s*Outlook[^\n]*",
    # OCR slide artifacts
    r"SQL\s*DAY\s*\d+\s*pdf",
    r"Slide\s*\d+",
    r"Page\s*\d+",
    r"^\s*\d+\s*of\s*\d+\s*$",
    # Weather / system info (OCR noise from screen captures)
    r"Partly\s*sunny",
    r"\bSunny\b",
    r"High\s*UV",
    r"Very\s*high\s*UV",
    r"\bENG\b",
    r"\bIN\b",
    # Timestamps
    r"\d{2}\.\d{2}\s*(PM|AM)",
    r"\d{2}-\d{2}-\d{4}",
    r"\d{2}/\d{2}/\d{4}",
    r"\d{2}:\d{2}:\d{2}",
    # File extensions in text
    r"\b\w+\.(jpg|jpeg|png|gif|bmp|pdf|txt|mp4|mp3|wav)\b",
    # Random single chars and noise
    r"@File|OFile",
    r"\bTABS\b",
    r"\bCRLF\b",
    r"\bUTF-8\b",
    r"^\s*\d+%\s*$",
    r"0f\s*\d+|of\s*\d+",
    # UI text
    r"Select\s*Repository",
    r"Command\s*Prompt",
    r"Microsoft\s*Windows\s*\[Version[^\n]*",
    r"All\s*rights\s*reserved[^\n]*",
    r"Object\s*Explorer",
    r"Connected\.",
    r"\(local\)",
    r"Ready\s*$",
    r"No\s*issues\s*found",
    r"Breaking\s*news[^\n]*",
    r"Gaurav\s*Mehta",
    # URL-like paths
    r"https?://[^\s]+",
    r"ftp://[^\s]+",
]


class ContextCompressor:
    def __init__(self):
        combined = r"(?:{})".format("|".join(NOISE_PATTERNS))
        self.noise_re = re.compile(combined, re.IGNORECASE | re.MULTILINE)

    def compress(
        self,
        question: str,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        compressed = []
        for r in results:
            cleaned = self._remove_noise(r.text)
            cleaned = cleaned.strip()
            if len(cleaned) > 30:
                compressed.append(
                    RetrievalResult(
                        text=cleaned,
                        source=self._clean_source_name(r.source),
                        score=r.score,
                        rank=r.rank,
                    )
                )
        return compressed

    def _clean_source_name(self, source: str) -> str:
        # Remove file extensions
        source = re.sub(r"\.(jpg|jpeg|png|gif|bmp|pdf|txt|mp4|mp3)", "", source)
        # Remove OCR prefix
        source = re.sub(r"^ocr[\s_]", "", source, flags=re.IGNORECASE)
        # Remove path segments
        source = re.sub(r"^[A-Z]:[/\\]", "", source)
        source = re.sub(r"[/\\]", " - ", source)
        # Remove UUIDs/hashes
        source = re.sub(r"[0-9a-f]{8,}-[0-9a-f]{4,}-[0-9a-f]{4,}", "", source)
        # Clean up multiple spaces and dashes
        source = re.sub(r"\s+", " ", source)
        source = source.strip().strip("-").strip()
        return source if source else "Lecture Content"

    def _remove_noise(self, text: str) -> str:
        text = self.noise_re.sub("", text)
        # Remove lines that are mostly non-alphanumeric
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if not stripped or len(stripped) < 3:
                continue
            if stripped.isdigit():
                continue
            # Skip lines that are mostly symbols or noise
            alpha_ratio = sum(c.isalpha() for c in stripped) / max(len(stripped), 1)
            if alpha_ratio < 0.3:
                continue
            cleaned.append(stripped)
        # Deduplicate while preserving order
        return "\n".join(dict.fromkeys(cleaned))
