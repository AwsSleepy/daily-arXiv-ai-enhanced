"""WeChat push channel — supports WeCom bot and PushPlus."""

import sys
import requests
from typing import List, Dict, Optional

from base import AbstractPushChannel
import formatter


class WeChatPushChannel(AbstractPushChannel):
    """Push to WeChat via WeCom bot webhook or PushPlus API."""

    def __init__(
        self,
        webhook_url: Optional[str] = None,
        method: str = "wecom_bot",
        key: Optional[str] = None,
    ):
        self.webhook_url = webhook_url
        self.method = method
        self.key = key

    def channel_name(self) -> str:
        return f"wechat ({self.method})"

    def send(self, papers: List[Dict], date: str) -> bool:
        if self.method == "wecom_bot":
            return self._send_wecom(papers, date)
        elif self.method == "pushplus":
            return self._send_pushplus(papers, date)
        elif self.method == "serverchan":
            return self._send_serverchan(papers, date)
        else:
            print(f"Unknown wechat method: {self.method}", file=sys.stderr)
            return False

    def _send_wecom(self, papers: List[Dict], date: str) -> bool:
        """Send via WeCom bot markdown webhook. Splits long messages."""
        if not self.webhook_url:
            print("WECHAT_WEBHOOK_URL not set", file=sys.stderr)
            return False

        messages = formatter.build_wecom_messages(papers, date)
        success = True
        for i, msg in enumerate(messages):
            payload = {
                "msgtype": "markdown",
                "markdown": {"content": msg},
            }
            try:
                resp = requests.post(self.webhook_url, json=payload, timeout=15)
                resp_data = resp.json()
                if resp.status_code == 200 and resp_data.get("errcode") == 0:
                    print(f"WeCom msg {i+1}/{len(messages)} sent OK", file=sys.stderr)
                else:
                    print(f"WeCom msg {i+1} failed: {resp.status_code} {resp_data}", file=sys.stderr)
                    success = False
            except Exception as e:
                print(f"WeCom msg {i+1} error: {e}", file=sys.stderr)
                success = False
        return success

    def _send_pushplus(self, papers: List[Dict], date: str) -> bool:
        """Send via PushPlus (personal WeChat)."""
        if not self.key:
            print("PUSH_WECHAT_KEY not set for pushplus", file=sys.stderr)
            return False

        content = formatter.build_text_digest(papers, date)
        payload = {
            "token": self.key,
            "title": f"Daily Robotics Papers | {date}",
            "content": content,
            "template": "markdown",
        }
        try:
            resp = requests.post("https://www.pushplus.plus/send", json=payload, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 200:
                    print("PushPlus sent OK", file=sys.stderr)
                    return True
                else:
                    print(f"PushPlus error: {data}", file=sys.stderr)
                    return False
            print(f"PushPlus HTTP {resp.status_code}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"PushPlus error: {e}", file=sys.stderr)
            return False

    def _send_serverchan(self, papers: List[Dict], date: str) -> bool:
        """Send via Server酱 (personal WeChat)."""
        if not self.key:
            print("PUSH_WECHAT_KEY not set for serverchan", file=sys.stderr)
            return False

        content = formatter.build_text_digest(papers, date)
        url = f"https://sctapi.ftqq.com/{self.key}.send"
        payload = {
            "title": f"Daily Robotics Papers | {date}",
            "desp": content,
        }
        try:
            resp = requests.post(url, data=payload, timeout=15)
            if resp.status_code == 200:
                print("ServerChan sent OK", file=sys.stderr)
                return True
            print(f"ServerChan HTTP {resp.status_code}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"ServerChan error: {e}", file=sys.stderr)
            return False
