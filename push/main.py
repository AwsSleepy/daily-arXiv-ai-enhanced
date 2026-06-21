#!/usr/bin/env python3
"""Push entry point — reads filtered JSONL and sends to configured channels."""

import os
import sys
import json
import argparse
from typing import List, Dict

from wechat import WeChatPushChannel


def load_filtered_papers(path: str) -> List[Dict]:
    """Load filtered JSONL (only relevant papers)."""
    papers = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                papers.append(json.loads(line))
    return papers


def parse_args():
    parser = argparse.ArgumentParser(description="Push filtered papers to IM channels")
    parser.add_argument("--data", type=str, required=True, help="Filtered JSONL file")
    parser.add_argument("--dry-run", action="store_true", help="Print messages without sending")
    parser.add_argument("--channel", type=str, default="wechat", help="Channel: wechat (default)")
    return parser.parse_args()


def main():
    args = parse_args()

    # Load papers
    if not os.path.exists(args.data):
        print(f"Filtered file not found: {args.data}", file=sys.stderr)
        sys.exit(1)

    papers = load_filtered_papers(args.data)
    if not papers:
        print("No relevant papers to push", file=sys.stderr)
        sys.exit(0)

    # Get today's date from filename or system
    import re
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(args.data))
    today = date_match.group(1) if date_match else "unknown"

    # Build channel list
    channels = []

    if args.channel == "wechat":
        webhook_url = os.environ.get("WECHAT_WEBHOOK_URL")
        method = os.environ.get("PUSH_WECHAT_METHOD", "wecom_bot")
        push_key = os.environ.get("PUSH_WECHAT_KEY")
        if webhook_url or push_key:
            channels.append(WeChatPushChannel(
                webhook_url=webhook_url,
                method=method,
                key=push_key,
            ))

    # Dry-run: show preview regardless of channel config
    if args.dry_run:
        from formatter import build_full_digest, build_wecom_messages
        print("\n--- DRY RUN: Full digest preview ---")
        print(build_full_digest(papers, today))
        print("\n--- DRY RUN: WeCom messages ---")
        for i, msg in enumerate(build_wecom_messages(papers, today)):
            print(f"\n[Message {i+1}, {len(msg.encode('utf-8'))} bytes]")
            print(msg)
        print("\n--- DRY RUN END ---")
        return

    # Send for real
    if not channels:
        print("No push channels configured. Set WECHAT_WEBHOOK_URL or PUSH_WECHAT_KEY.", file=sys.stderr)
        sys.exit(1)

    for ch in channels:
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"Channel: {ch.channel_name()}", file=sys.stderr)
        print(f"Papers: {len(papers)} | Date: {today}", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        success = ch.send(papers, today)
        status = "✅ OK" if success else "❌ FAILED"
        print(f"\nPush [{ch.channel_name()}]: {status}", file=sys.stderr)


if __name__ == "__main__":
    main()
