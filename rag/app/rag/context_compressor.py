import logging
import re

from app.models.retrieval_result import RetrievalResult

logger = logging.getLogger(__name__)


NOISE_PATTERNS = [
    r"Microsoft\s*Teams",
    r"Recorded\s*by",
    r"Organized\s*by",
    r"Gaurav\s*Mehta",
    r"Ask\s*Copilot",
    r"^\s*Chat\s*$",
    r"Type\s*a\s*message",
    r"\bENG\b",
    r"\bIN\b",
    r"Partly\s*sunny",
    r"\bSunny\b",
    r"High\s*UV",
    r"Very\s*high\s*UV",
    r"C[:/]Users/Gaurav/",
    r"AppData/Local/Microsoft/Windows/INetCache/",
    r"Content\.Outlook",
    r"SQL\s*DAY\s*1\s*pdf",
    r"@File|OFile",
    r"Breaking\s*news",
    r"Select\s*Repository",
    r"Command\s*Prompt",
    r"Microsoft\s*Windows\s*\[Version",
    r"Try\s*the\s*new\s*Outlook",
    r"Object\s*Explorer",
    r"\bTABS\b",
    r"\bCRLF\b",
    r"\bUTF-8\b",
    r"Connected\.",
    r"\(local\)",
    r"\d{2}\.\d{2}\s*(PM|AM)",
    r"\d{2}-\d{2}-\d{4}",
    r"\d{2}\s*[*C'\u00b0]C",
    r"^\s*\d+%\s*$",
    r"0f\s*\d+|of\s*\d+",
]


class ContextCompressor:
    def __init__(self):
        self.compiled = [re.compile(p, re.IGNORECASE | re.MULTILINE) for p in NOISE_PATTERNS]

    def compress(
        self,
        question: str,
        results: list[RetrievalResult],
    ) -> list[RetrievalResult]:
        compressed = []
        for r in results:
            cleaned = self._remove_noise(r.text)
            cleaned = self._deduplicate_lines(cleaned)
            cleaned = cleaned.strip()
            if len(cleaned) > 20:
                compressed.append(
                    RetrievalResult(
                        text=cleaned,
                        source=r.source,
                        score=r.score,
                        rank=r.rank,
                    )
                )
        return compressed

    def _remove_noise(self, text: str) -> str:
        for pattern in self.compiled:
            text = pattern.sub("", text)
        lines = text.split("\n")
        cleaned = []
        for line in lines:
            stripped = line.strip()
            if len(stripped) < 3:
                continue
            if stripped.isdigit():
                continue
            cleaned.append(stripped)
        return "\n".join(cleaned)

    def _deduplicate_lines(self, text: str) -> str:
        seen = set()
        lines = text.split("\n")
        result = []
        for line in lines:
            stripped = line.strip().lower()
            if stripped and stripped not in seen:
                seen.add(stripped)
                result.append(line)
        return "\n".join(result)
