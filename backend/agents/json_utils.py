"""Robust JSON extraction from LLM responses that may contain markdown fences or extra text."""
import json
import re


def _strip_markdown_fences(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers."""
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


def extract_json_object(text: str) -> dict | None:
    """Extract the first JSON object {...} from LLM text. Returns None on failure."""
    text = _strip_markdown_fences(text)
    # Non-greedy: match first complete {...}
    match = re.search(r"\{.*?\}", text, re.DOTALL)
    if match:
        # Try progressively longer matches (non-greedy may be too short for nested objects)
        candidate = match.group()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Fallback: try to find balanced braces
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None


def extract_json_array(text: str) -> list | None:
    """Extract the first JSON array [...] from LLM text. Returns None on failure."""
    text = _strip_markdown_fences(text)
    # Balanced bracket matching
    start = text.find("[")
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "[":
            depth += 1
        elif text[i] == "]":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    return None
