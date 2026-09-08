"""雪之下雪乃 · 网页抓取工具
用途：请求指定 URL，返回状态码与正文文本（去标签）。
限制：只能访问已知地址，不提供搜索功能。
"""

import re
import socket
import urllib.request

socket.setdefaulttimeout(10)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"


def fetch(url: str, limit: int = 3000) -> str:
    """请求 url，返回纯文本内容。"""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as r:
        raw = r.read()
        charset = r.headers.get_content_charset() or "utf-8"
        html = raw.decode(charset, errors="replace")

    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&nbsp;?", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return f"[{r.status}] {url}\n{text[:limit]}"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("用法: python fetch.py <url>")
    else:
        try:
            print(fetch(sys.argv[1]))
        except Exception as e:
            print(f"失败: {type(e).__name__}: {e}")
