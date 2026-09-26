from __future__ import annotations


def parse_match_clock(value) -> int | None:
    """Convert an ascending MM:SS (or MM.SS) match clock to seconds."""
    text = str(value or "").strip().replace(".", ":")
    if not text:
        return None
    try:
        if ":" in text:
            parts = text.split(":")
            if len(parts) != 2:
                return None
            minutes, seconds = int(parts[0]), int(parts[1])
        elif text.isdigit() and len(text) >= 3:
            minutes, seconds = int(text[:-2]), int(text[-2:])
        else:
            return None
        if minutes < 0 or not 0 <= seconds < 60:
            return None
        return minutes * 60 + seconds
    except (TypeError, ValueError):
        return None


def format_seconds(seconds) -> str:
    seconds = max(0, int(seconds or 0))
    minutes, remainder = divmod(seconds, 60)
    return f"{minutes}:{remainder:02d}"
