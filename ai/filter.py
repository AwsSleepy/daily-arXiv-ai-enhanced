import os
import sys
import json
import argparse
import re
import yaml
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Set, Optional

from tqdm import tqdm

from langchain_openai import ChatOpenAI
from langchain_core.exceptions import OutputParserException
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from filter_structure import RelevanceFilter


# ─── Config loader ───────────────────────────────────────────────

def load_config(path: str) -> dict:
    """加载 topics.yaml 配置"""
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    _validate_config(config)
    return config


def _validate_config(config: dict):
    """基本校验配置结构"""
    assert "topics" in config, "config must have 'topics' key"
    for t in config["topics"]:
        assert "id" in t, f"topic missing 'id': {t}"
        assert "name" in t, f"topic missing 'name': {t}"
    if "watched" in config:
        if "labs" in config["watched"]:
            for lab in config["watched"]["labs"]:
                assert "name" in lab and "keywords" in lab, f"lab missing fields: {lab}"
        if "authors" in config["watched"]:
            for a in config["watched"]["authors"]:
                assert "name" in a, f"author missing 'name': {a}"
    print(f"Loaded {len(config['topics'])} topics, config valid", file=sys.stderr)


# ─── Stage 1: watch list string match ────────────────────────────

def _normalize(text: str) -> str:
    """小写去空格，用于匹配"""
    return text.lower().strip()


def stage1_watchlist_match(paper: dict, config: dict) -> Optional[dict]:
    """
    阶段 1：零 LLM 成本的字符串匹配。
    检查论文的 authors/text 是否命中 watched.labs 或 watched.authors。
    返回匹配信息，或 None（未命中）。
    """
    watched = config.get("watched", {})
    if not watched:
        return None

    # 构建文本池：标题 + 作者 + 摘要
    text_parts = []
    if paper.get("title"):
        text_parts.append(str(paper["title"]))
    if paper.get("authors"):
        text_parts.append(str(paper["authors"]))
    if paper.get("summary"):
        text_parts.append(str(paper["summary"]))
    # AI 摘要如果有也加进去
    ai = paper.get("AI", {})
    if ai.get("tldr"):
        text_parts.append(ai["tldr"])
    if ai.get("method"):
        text_parts.append(ai["method"])
    full_text = " ".join(text_parts)
    full_text_lower = _normalize(full_text)

    matched_labs = []
    # 检查 labs
    for lab in watched.get("labs", []):
        for kw in lab.get("keywords", []):
            if _normalize(kw) in full_text_lower:
                matched_labs.append(lab["name"])
                break  # 一个 lab 只计一次

    matched_authors = []
    # 检查 authors
    authors_text = _normalize(str(paper.get("authors", "")))
    for author in watched.get("authors", []):
        if _normalize(author["name"]) in authors_text:
            matched_authors.append(author["name"])

    if matched_labs or matched_authors:
        return {
            "is_relevant": True,
            "matched_topics": [],
            "from_watchlist": True,
            "confidence": 1.0,
            "reason": f"关注列表匹配 — Labs: {matched_labs}; Authors: {matched_authors}",
        }

    return None


# ─── Stage 2: LLM filtering ──────────────────────────────────────

def _build_topic_context(config: dict) -> str:
    """将 topics 格式化为给 LLM 的提示文本"""
    lines = []
    for t in config.get("topics", []):
        topic_id = t["id"]
        name = t["name"]
        desc = t.get("description", "")
        kws = ", ".join(t.get("keywords", [])[:8])  # 只展示前 8 个关键词
        lines.append(f"### {topic_id}: {name}\n描述：{desc}\n关键词：{kws}\n")
    return "\n".join(lines)


def _build_watched_context(config: dict) -> str:
    """将关注列表格式化为给 LLM 的提示"""
    watched = config.get("watched", {})
    if not watched:
        return "（无特别关注列表）"
    lines = ["以下组/作者的工作优先推送："]
    for lab in watched.get("labs", []):
        lines.append(f"- Lab: {lab['name']} ({'; '.join(lab.get('keywords', [])[:5])})")
    for a in watched.get("authors", []):
        lines.append(f"- Author: {a['name']} ({a.get('note', '')})")
    return "\n".join(lines)


SYSTEM_PROMPT = """\
你是一个机器人学论文审稿人。请根据以下论文信息，判断它是否属于给定的研究方向。

研究方向定义：
{topic_definitions}

关注列表（来自这些组/作者的工作优先推送）：
{watched_context}

请判断这篇论文是否与上述任一研究方向相关。注意：
1. 宽松匹配——如果论文的技术方法可能应用于某方向，也可标记
2. 一篇论文可以属于多个方向（matched_topics 填对应的 id）
3. 如果来自关注列表中的组/作者，标记 from_watchlist=true
4. 给出置信度（0-1）和一句话理由"""


def stage2_llm_filter(chain, paper: dict) -> dict:
    """阶段 2：LLM 判断相关性"""
    try:
        result: RelevanceFilter = chain.invoke({
            "title": paper.get("title", ""),
            "authors": paper.get("authors", ""),
            "summary": paper.get("summary", ""),
            "tldr": paper.get("AI", {}).get("tldr", ""),
            "method": paper.get("AI", {}).get("method", ""),
        })
        return result.model_dump()
    except (OutputParserException, Exception) as e:
        print(f"LLM filter failed for {paper.get('id', 'unknown')}: {e}", file=sys.stderr)
        return {
            "is_relevant": False,
            "matched_topics": [],
            "from_watchlist": False,
            "confidence": 0.0,
            "reason": f"Filter failed: {str(e)[:100]}",
        }


# ─── Main pipeline ────────────────────────────────────────────────

def process_single_paper(chain, paper: dict, config: dict) -> dict:
    """
    处理单篇论文：先阶段 1（字符串匹配），未命中则阶段 2（LLM）。
    返回更新后的 paper dict（带有 AI 过滤字段）。
    """
    # Stage 1: watch list check
    stage1_result = stage1_watchlist_match(paper, config)
    if stage1_result is not None:
        paper.setdefault("AI", {})
        paper["AI"]["is_relevant"] = stage1_result["is_relevant"]
        paper["AI"]["matched_topics"] = stage1_result["matched_topics"]
        paper["AI"]["from_watchlist"] = stage1_result["from_watchlist"]
        paper["AI"]["confidence"] = stage1_result["confidence"]
        paper["AI"]["reason"] = stage1_result["reason"]
        return paper

    # Stage 2: LLM filtering (skip if chain is None, i.e. stage1-only mode)
    if chain is not None:
        filter_result = stage2_llm_filter(chain, paper)
        paper.setdefault("AI", {})
        paper["AI"]["is_relevant"] = filter_result.get("is_relevant", False)
        paper["AI"]["matched_topics"] = filter_result.get("matched_topics", [])
        paper["AI"]["from_watchlist"] = filter_result.get("from_watchlist", False)
        paper["AI"]["confidence"] = filter_result.get("confidence", 0.0)
        paper["AI"]["reason"] = filter_result.get("reason", "")
    else:
        # Stage1-only: mark as not relevant since stage 1 didn't match
        paper.setdefault("AI", {})
        paper["AI"]["is_relevant"] = False
        paper["AI"]["matched_topics"] = []
        paper["AI"]["from_watchlist"] = False
        paper["AI"]["confidence"] = 0.0
        paper["AI"]["reason"] = "Stage1: no watchlist match (LLM skipped)"
    return paper


def process_all_items(
    data: List[Dict],
    config: dict,
    model_name: str,
    max_workers: int = 2,
) -> List[Dict]:
    """并行处理所有论文，执行两阶段过滤"""
    # 构建 LLM chain
    prompt_template = ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template(
            "论文信息：\n- 标题：{title}\n- 作者：{authors}\n- 摘要：{summary}\n- TL;DR：{tldr}\n- 方法：{method}"
        ),
    ])

    llm = ChatOpenAI(model=model_name, temperature=0.1).with_structured_output(
        RelevanceFilter, method="function_calling"
    )
    chain = prompt_template | llm

    # 预注入静态上下文到系统 prompt
    topic_definitions = _build_topic_context(config)
    watched_context = _build_watched_context(config)
    chain = chain.partial(
        topic_definitions=topic_definitions,
        watched_context=watched_context,
    )

    processed_data = [None] * len(data)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {
            executor.submit(process_single_paper, chain, item, config): idx
            for idx, item in enumerate(data)
        }
        for future in tqdm(as_completed(future_to_idx), total=len(data), desc="Filtering"):
            idx = future_to_idx[future]
            try:
                processed_data[idx] = future.result()
            except Exception as e:
                print(f"Item at index {idx} exception: {e}", file=sys.stderr)
                processed_data[idx] = data[idx]
                processed_data[idx].setdefault("AI", {})
                processed_data[idx]["AI"]["is_relevant"] = False
                processed_data[idx]["AI"]["matched_topics"] = []
                processed_data[idx]["AI"]["from_watchlist"] = False
                processed_data[idx]["AI"]["confidence"] = 0.0
                processed_data[idx]["AI"]["reason"] = "Filter error"

    return processed_data


# ─── CLI ──────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="AI relevance filter for arXiv papers")
    parser.add_argument("--data", type=str, required=True, help="AI-enhanced JSONL file")
    parser.add_argument("--topics", type=str, default="config/topics.yaml", help="topic config YAML")
    parser.add_argument("--max-workers", type=int, default=2, help="max parallel LLM workers")
    parser.add_argument("--model", type=str, default=None, help="LLM model (default: $MODEL_NAME or deepseek-chat)")
    parser.add_argument("--stage1-only", action="store_true", help="Only run stage 1 (string matching), skip LLM")
    return parser.parse_args()


def main():
    args = parse_args()
    model_name = args.model or os.environ.get("MODEL_NAME", "deepseek-chat")
    config = load_config(args.topics)

    # Read data
    data = []
    with open(args.data, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    print(f"Loaded {len(data)} papers from {args.data}", file=sys.stderr)

    # Process
    if args.stage1_only:
        print("Running STAGE 1 ONLY (no LLM calls)", file=sys.stderr)
        processed_data = []
        for paper in tqdm(data, desc="Stage1 matching"):
            processed = process_single_paper(None, paper, config)
            processed_data.append(processed)
    else:
        processed_data = process_all_items(data, config, model_name, args.max_workers)

    # Figure out output paths
    # Input: ../data/2026-06-21_AI_enhanced_Chinese.jsonl
    # Filtered output: ../data/2026-06-21_filtered.jsonl
    # Enhanced output (overwrite): same as input
    import os as _os
    data_dir = _os.path.dirname(args.data)
    base = _os.path.basename(args.data)
    # Extract date prefix: "2026-06-21" from "2026-06-21_AI_enhanced_Chinese.jsonl"
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", base)
    if date_match:
        date_str = date_match.group(1)
        filtered_file = _os.path.join(data_dir, f"{date_str}_filtered.jsonl")
    else:
        filtered_file = _os.path.join(data_dir, base.replace(".jsonl", "_filtered.jsonl"))
    enhanced_file = args.data  # overwrite the original enhanced file

    # Write filtered file (only relevant papers)
    relevant_count = 0
    watchlist_count = 0
    with open(filtered_file, "w", encoding="utf-8") as f:
        for paper in processed_data:
            if paper is not None and paper.get("AI", {}).get("is_relevant"):
                f.write(json.dumps(paper, ensure_ascii=False) + "\n")
                relevant_count += 1
                if paper.get("AI", {}).get("from_watchlist"):
                    watchlist_count += 1

    # Overwrite enhanced file with filter fields included
    enhanced_file = args.data.replace("_filtered.jsonl", ".jsonl")
    if enhanced_file != args.data:
        with open(enhanced_file, "w", encoding="utf-8") as f:
            for paper in processed_data:
                if paper is not None:
                    f.write(json.dumps(paper, ensure_ascii=False) + "\n")
        print(f"Updated enhanced data: {enhanced_file}", file=sys.stderr)

    print(f"Filtered: {relevant_count}/{len(data)} relevant, {watchlist_count} from watchlist", file=sys.stderr)
    print(f"Output: {filtered_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
