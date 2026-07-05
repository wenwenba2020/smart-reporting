"""
ChatExportAdapter — parses chat exports (WeChat / WeCom / DingTalk / Feishu)
into structured SourceDocument instances with date-grouped Markdown output.
"""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Optional

from backend.core.datasource.base import DataSourceAdapter, register_adapter
from backend.core.models import SourceDocument

# ---------------------------------------------------------------------------
# Keyword sets for supports()
# ---------------------------------------------------------------------------

_CHAT_KEYWORDS = [
    "微信", "wechat",
    "企业微信", "wecom",
    "钉钉", "dingtalk",
    "飞书", "feishu", "lark",
    "聊天", "chat",
]


# ---------------------------------------------------------------------------
# Message patterns
# ---------------------------------------------------------------------------

# WeChat classic: "YYYY-MM-DD HH:MM:SS Name"
_WECHAT_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$"
)

# WeCom style:  "Name  YYYY-MM-DD HH:MM:SS" or "Name(昵称)  YYYY-MM-DD HH:MM:SS"
_WECOM_RE = re.compile(
    r"^(.+?)\s{2,}(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}(?::\d{2})?)$"
)

# DingTalk style: "Name  YYYY-MM-DD HH:MM:SS"
_DINGTALK_RE = re.compile(
    r"^(.+?)\s{2,}(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}(?::\d{2})?)$"
)

# Feishu / Lark style: tab-delimited or CSV with time column at start
_FEISHU_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{1,2}:\d{2}(?::\d{2})?)\t(.+?)\t(.+)$"
)

# Date-only line (for date separators in some exports)
_DATE_SEP_RE = re.compile(r"^(\d{4}[-/年]\d{1,2}[-/月]\d{1,2})[日号]?\s*(?:周[一二三四五六日])?$")

# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


@register_adapter
class ChatExportAdapter(DataSourceAdapter):
    source_type = "chat_export"

    # ------------------------------------------------------------------
    # supports
    # ------------------------------------------------------------------

    def supports(self, filename: str) -> bool:
        fname_lower = filename.lower()
        return any(kw.lower() in fname_lower for kw in _CHAT_KEYWORDS)

    # ------------------------------------------------------------------
    # parse
    # ------------------------------------------------------------------

    async def parse(
        self,
        file_path: str,
        filename: str,
        metadata: Optional[dict] = None,
    ) -> SourceDocument:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            raw_text = fh.read()

        lines = raw_text.split("\n")

        # Detect format by scanning the first N non-empty lines
        format_type = self._detect_format(raw_text, lines)

        if format_type == "feishu":
            parsed = self._parse_feishu(raw_text, lines)
        elif format_type in ("wechat", "wecom", "dingtalk"):
            if format_type == "wechat":
                parsed = self._parse_generic(lines, _WECHAT_RE, time_first=True)
            elif format_type == "wecom":
                parsed = self._parse_generic(lines, _WECOM_RE, time_first=False)
            else:
                parsed = self._parse_generic(lines, _DINGTALK_RE, time_first=False)
        else:
            # Fallback: treat as plain text with date-grouping attempt
            parsed = self._parse_fallback(raw_text)

        # Build structured Markdown
        md = self._build_markdown(filename, format_type, parsed)

        result_meta = (metadata or {}).copy()
        result_meta["chat_format"] = format_type

        return SourceDocument(
            id=str(uuid.uuid4()),
            title=filename,
            content=md,
            source_type=self.source_type,
            metadata=result_meta,
        )

    # ------------------------------------------------------------------
    # Format detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_format(raw_text: str, lines: list[str]) -> str:
        """Determine the chat export format by scanning lines.

        Returns one of: "wechat", "wecom", "dingtalk", "feishu", "unknown".
        """
        # Feishu: tabs present and pattern matches
        if "\t" in raw_text:
            for line in lines[:50]:
                if _FEISHU_RE.match(line.strip()):
                    return "feishu"

        # Count matches for each format in the first 50 non-empty lines
        counts: dict[str, int] = {"wechat": 0, "wecom": 0, "dingtalk": 0}
        non_empty = [l for l in lines[:100] if l.strip()]
        for line in non_empty[:50]:
            s = line.strip()
            if _WECHAT_RE.match(s):
                counts["wechat"] += 1
            if _WECOM_RE.match(s):
                counts["wecom"] += 1
            if _DINGTALK_RE.match(s):
                counts["dingtalk"] += 1

        # Return the format with the most matches (minimum 1)
        best = max(counts, key=counts.get)  # type: ignore[arg-type]
        if counts[best] > 0:
            return best
        return "unknown"

    # ------------------------------------------------------------------
    # Generic parser (WeChat / WeCom / DingTalk)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_generic(
        lines: list[str],
        msg_re: re.Pattern,
        time_first: bool,
    ) -> dict:
        """Parse chat text where each message starts with a timestamp+name header line.

        Returns dict with keys: participants (set), messages_by_date (dict),
        total_messages (int), raw_messages (list of dicts).
        """
        participants: set[str] = set()
        messages: list[dict] = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            m = msg_re.match(line)
            if m:
                if time_first:
                    date_str, time_str, name = m.groups()
                else:
                    name, datetime_str = m.groups()
                    # Split datetime into date and time
                    parts = datetime_str.strip().split()
                    date_str = parts[0] if parts else ""
                    time_str = parts[1] if len(parts) > 1 else ""

                # Collect message body (subsequent non-header lines)
                body_lines: list[str] = []
                i += 1
                while i < len(lines):
                    next_line = lines[i]
                    if msg_re.match(next_line.strip()):
                        break
                    if next_line.strip():
                        body_lines.append(next_line.strip())
                    i += 1

                name = name.strip()
                participants.add(name)
                messages.append({
                    "date": date_str,
                    "time": time_str,
                    "sender": name,
                    "body": "\n".join(body_lines),
                })
            else:
                # skip blank / unrecognized lines
                i += 1

        # Group by date
        by_date: dict[str, list[dict]] = defaultdict(list)
        for msg in messages:
            by_date[msg["date"]].append(msg)

        return {
            "participants": participants,
            "messages_by_date": dict(by_date),
            "total_messages": len(messages),
            "raw_messages": messages,
        }

    # ------------------------------------------------------------------
    # Feishu / Lark parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_feishu(raw_text: str, lines: list[str]) -> dict:
        """Parse Feishu tab-delimited export.

        Expected tab-delimited format: time \\t sender \\t content
        """
        participants: set[str] = set()
        messages: list[dict] = []
        by_date: dict[str, list[dict]] = defaultdict(list)

        for line in lines:
            line = line.strip()
            m = _FEISHU_RE.match(line)
            if m:
                datetime_str, sender, body = m.groups()
                parts = datetime_str.strip().split()
                date_str = parts[0]
                time_str = parts[1] if len(parts) > 1 else ""
                sender = sender.strip()
                participants.add(sender)
                msg = {
                    "date": date_str,
                    "time": time_str,
                    "sender": sender,
                    "body": body.strip(),
                }
                messages.append(msg)
                by_date[date_str].append(msg)
            elif line:
                # Attachment to previous message or header line
                if messages:
                    messages[-1]["body"] += "\n" + line

        return {
            "participants": participants,
            "messages_by_date": dict(by_date),
            "total_messages": len(messages),
            "raw_messages": messages,
        }

    # ------------------------------------------------------------------
    # Fallback parser
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_fallback(text: str) -> dict:
        """Try to extract any date-grouped messages from arbitrary text."""
        participants: set[str] = set()
        messages: list[dict] = []
        by_date: dict[str, list[dict]] = defaultdict(list)
        current_date: str = "Unknown"

        for line in text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            date_m = _DATE_SEP_RE.match(line)
            if date_m:
                current_date = date_m.group(1).replace("年", "-").replace("月", "-").replace("日", "")
                continue

            # Look for any name-colon pattern like "Name: message"
            name_colon = re.match(r"^(.+?)[：:]\s*(.*)$", line)
            if name_colon:
                sender = name_colon.group(1).strip()
                body = name_colon.group(2).strip()
                participants.add(sender)
                msg = {"date": current_date, "time": "", "sender": sender, "body": body}
                messages.append(msg)
                by_date[current_date].append(msg)
            elif messages:
                messages[-1]["body"] += "\n" + line

        return {
            "participants": participants,
            "messages_by_date": dict(by_date),
            "total_messages": len(messages),
            "raw_messages": messages,
        }

    # ------------------------------------------------------------------
    # Markdown builder
    # ------------------------------------------------------------------

    @staticmethod
    def _build_markdown(filename: str, format_type: str, parsed: dict) -> str:
        parts: list[str] = []

        parts.append(f"# Chat Export: {Path(filename).stem}")
        parts.append(f"**Format**: {format_type}")
        parts.append(
            f"**Participants** ({len(parsed['participants'])}): "
            + ", ".join(sorted(parsed["participants"]))
        )
        parts.append(f"**Total Messages**: {parsed['total_messages']}")
        parts.append("")

        # Date-organized content
        for date_str in sorted(parsed["messages_by_date"].keys()):
            msgs = parsed["messages_by_date"][date_str]
            parts.append(f"## {date_str} ({len(msgs)} messages)")
            parts.append("")
            for msg in msgs:
                time_part = f" {msg['time']}" if msg["time"] else ""
                parts.append(
                    f"**{msg['sender']}**{time_part}:\n"
                    f"{msg['body']}\n"
                )

        return "\n".join(parts)
