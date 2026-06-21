"""Message formatting for push channels.

Converts filtered paper lists into Markdown/text messages,
with topic grouping, priority sorting, and length-aware segmentation."""

import os
from typing import List, Dict, Tuple

# ─── Constants ───────────────────────────────────────────────────

TOPIC_EMOJI = {
    "vla": "🔥",
    "wam": "🌐",
    "navigation": "🚗",
    "motion-planning": "📐",
    "physics-motion": "🏃",
    "whole-body-control": "🤖",
    "other": "📌",
}
DEFAULT_EMOJI = "📄"

WECOM_MAX_BYTES = 4096
DEFAULT_TOP_N = int(os.environ.get("PUSH_TOP_N", "5"))
DEFAULT_MIN_CONFIDENCE = float(os.environ.get("PUSH_MIN_CONFIDENCE", "0.6"))
SUMMARY_MAX_LEN = int(os.environ.get("PUSH_SUMMARY_LENGTH", "120"))

TOPIC_NAME_MAP = {
    "vla": "VLA",
    "wam": "World Action Model",
    "navigation": "Navigation",
    "motion-planning": "Motion Planning",
    "physics-motion": "Physics Motion & Interaction",
    "whole-body-control": "Whole Body Control",
    "other": "Other Robotics",
}

# ─── Helpers ─────────────────────────────────────────────────────

def _truncate(text: str, max_len: int = SUMMARY_MAX_LEN) -> str:
    """Truncate text to max_len chars, preserving word boundaries."""
    if not text:
        return ""
    text = text.replace("\n", " ").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rsplit(" ", 1)[0] + "…"


def _paper_priority(paper: dict) -> tuple:
    """Sort key: watchlist first, then confidence descending."""
    ai = paper.get("AI", {})
    return (
        0 if ai.get("from_watchlist") else 1,  # 0 = watchlist first
        -(ai.get("confidence", 0)),             # high confidence first
    )


# ─── Group & Sort ────────────────────────────────────────────────

def group_by_topic(papers: List[Dict]) -> Dict[str, List[Dict]]:
    """Group papers by matched_topics. One paper can appear in multiple groups."""
    groups: Dict[str, List[Dict]] = {}
    for p in papers:
        ai = p.get("AI", {})
        topics = ai.get("matched_topics", [])
        if not topics:
            topics = ["other"]
        for topic_id in topics:
            groups.setdefault(topic_id, []).append(p)
    # Sort within each group
    for topic_id in groups:
        groups[topic_id].sort(key=_paper_priority)
    return groups


def sort_topics(groups: Dict[str, List[Dict]]) -> List[Tuple[str, List[Dict]]]:
    """Sort topic groups: most papers first."""
    return sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)


# ─── Message builders ────────────────────────────────────────────

def _paper_line(paper: dict) -> str:
    """Build one paper line with optional star for watchlist."""
    ai = paper.get("AI", {})
    star = "⭐ " if ai.get("from_watchlist") else ""
    arxiv_id = paper.get("id", "")
    title = paper.get("title", "Untitled")
    url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""
    tldr = _truncate(ai.get("tldr", ""))

    if url:
        line = f"- {star}[{title}]({url})\n"
    else:
        line = f"- {star}**{title}**\n"
    if tldr:
        line += f"  *{tldr}*\n"
    return line


def build_topic_section(topic_id: str, papers: List[Dict], top_n: int = DEFAULT_TOP_N) -> str:
    """Build a single topic's Markdown section."""
    emoji = TOPIC_EMOJI.get(topic_id, DEFAULT_EMOJI)
    name = TOPIC_NAME_MAP.get(topic_id, topic_id)
    count = len(papers)
    shown = min(count, top_n)

    section = f"{emoji} **{name}**（{count} 篇）\n"
    for p in papers[:top_n]:
        section += _paper_line(p)
    if count > top_n:
        section += f"  *… 还有 {count - top_n} 篇*\n"
    return section


def build_full_digest(papers: List[Dict], date: str, top_n: int = DEFAULT_TOP_N) -> str:
    """Build the complete Markdown digest message."""
    groups = group_by_topic(papers)
    ordered = sort_topics(groups)

    watchlist_count = sum(1 for p in papers if p.get("AI", {}).get("from_watchlist"))
    total_crawled = os.environ.get("TOTAL_CRAWLED", "?")

    lines = [f"📌 **Daily Robotics Papers | {date}**\n"]
    for topic_id, topic_papers in ordered:
        lines.append(build_topic_section(topic_id, topic_papers, top_n))
        lines.append("")

    lines.append("---")
    lines.append(f"📊 相关 {len(papers)} 篇 | ⭐关注列表 {watchlist_count} 篇")
    # Add link to GitHub Pages
    repo_owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")
    repo_name = os.environ.get("GITHUB_REPOSITORY_NAME", "daily-arXiv-ai-enhanced")
    if repo_owner:
        lines.append(f"[查看全部](https://{repo_owner}.github.io/{repo_name}/)")

    return "\n".join(lines)


def build_text_digest(papers: List[Dict], date: str, top_n: int = DEFAULT_TOP_N) -> str:
    """Build plain-text digest for PushPlus / Server酱 (no Markdown)."""
    groups = group_by_topic(papers)
    ordered = sort_topics(groups)

    watchlist_count = sum(1 for p in papers if p.get("AI", {}).get("from_watchlist"))

    lines = [f"Daily Robotics Papers | {date}", ""]
    for topic_id, topic_papers in ordered:
        name = TOPIC_NAME_MAP.get(topic_id, topic_id)
        lines.append(f"[{name}] ({len(topic_papers)} papers)")
        for p in topic_papers[:top_n]:
            star = "[☆] " if p.get("AI", {}).get("from_watchlist") else ""
            title = p.get("title", "Untitled")
            arxiv_id = p.get("id", "")
            url = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ""
            tldr = _truncate(p.get("AI", {}).get("tldr", ""))
            lines.append(f"  {star}{title}")
            if url:
                lines.append(f"  {url}")
            if tldr:
                lines.append(f"  {tldr}")
            lines.append("")
        if len(topic_papers) > top_n:
            lines.append(f"  ... +{len(topic_papers) - top_n} more")
            lines.append("")

    lines.append(f"--- Total: {len(papers)} relevant, {watchlist_count} from watchlist")
    return "\n".join(lines)


# ─── WeChat-specific segmentation ────────────────────────────────

def _count_bytes(text: str) -> int:
    """Count UTF-8 bytes of a string."""
    return len(text.encode("utf-8"))


def split_by_bytes(text: str, max_bytes: int = WECOM_MAX_BYTES) -> List[str]:
    """Split text into chunks, each under max_bytes. Split on newlines."""
    chunks = []
    current = ""
    for line in text.split("\n"):
        if _count_bytes(current + line + "\n") > max_bytes and current:
            chunks.append(current.rstrip())
            current = line + "\n"
        else:
            current += line + "\n"
    if current.strip():
        chunks.append(current.rstrip())
    return chunks


def build_wecom_messages(papers: List[Dict], date: str, top_n: int = DEFAULT_TOP_N) -> List[str]:
    """Build one or more WeChat markdown messages, segmented by byte limit."""
    full = build_full_digest(papers, date, top_n)
    chunks = split_by_bytes(full)
    # Add pagination if multiple chunks
    if len(chunks) > 1:
        for i, chunk in enumerate(chunks):
            chunks[i] = chunk + f"\n\n({i+1}/{len(chunks)})"
    return chunks
