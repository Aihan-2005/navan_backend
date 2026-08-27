import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TextChunk:
    order: int
    text: str

    @property
    def char_count(self) -> int:
        return len(self.text)


def normalize_text(text: str) -> str:
    text = text.replace("\x00", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def build_overview_sample(text: str, *, max_chars: int = 24000) -> str:
    text = normalize_text(text)
    if len(text) <= max_chars:
        return text

    part = max_chars // 3
    middle_start = max(0, (len(text) // 2) - (part // 2))
    return (
        "\n\n--- START SAMPLE ---\n"
        + text[:part]
        + (
            "\n\n--- MIDDLE SAMPLE ---\n"
            + text[middle_start : middle_start + part]
            + "\n\n--- END SAMPLE ---\n"
            + text[-part:]
        )
    )


def _split_large_block(block: str, max_chars: int) -> list[str]:
    if len(block) <= max_chars:
        return [block]

    parts: list[str] = []
    remaining = block.strip()

    while len(remaining) > max_chars:
        window = remaining[:max_chars]
        split_at = max(window.rfind(". "), window.rfind("! "), window.rfind("? "))
        if split_at < max_chars // 2:
            split_at = window.rfind(" ")
        if split_at < max_chars // 2:
            split_at = max_chars
        else:
            split_at += 1

        parts.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    if remaining:
        parts.append(remaining)

    return parts


def chunk_text(
    text: str,
    *,
    target_chars: int = 10000,
    max_chars: int = 14000,
) -> list[TextChunk]:
    if target_chars <= 0 or max_chars <= 0 or target_chars > max_chars:
        raise ValueError("Invalid chunk sizes.")

    text = normalize_text(text)
    if not text:
        return []

    raw_blocks = [block.strip() for block in re.split(r"\n\n+", text) if block.strip()]
    blocks: list[str] = []
    for block in raw_blocks:
        blocks.extend(_split_large_block(block, max_chars))

    chunks: list[TextChunk] = []
    current: list[str] = []
    current_size = 0

    def flush() -> None:
        nonlocal current, current_size
        if current:
            chunks.append(TextChunk(order=len(chunks) + 1, text="\n\n".join(current)))
            current = []
            current_size = 0

    for block in blocks:
        extra = len(block) + (2 if current else 0)
        if current and (current_size + extra > max_chars or current_size >= target_chars):
            flush()

        current.append(block)
        current_size += extra

    flush()
    return chunks
