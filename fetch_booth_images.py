"""owned.json（所持）と data.json（回せる）の BOOTH URL から商品画像（og:image）を取得し owned_images.json に保存する。
GitHub Actions から実行（ブラウザからは BOOTH を直接読めないため）。"""
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request

OWNED = "owned.json"
DATA = "data.json"
OUT = "owned_images.json"
MAX_FETCH = 500      # 1回の実行で取得する最大件数（残りは次回）
WAIT = 0.7           # 取得間隔（秒）


def booth_key(url):
    m = re.search(r"https?://[^\s　]+", url or "")
    if not m:
        return ""
    p = urllib.parse.urlsplit(m.group(0))
    host = (p.hostname or "").lower()
    if not (host == "booth.pm" or host.endswith(".booth.pm")):
        return ""
    return urllib.parse.urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path.rstrip("/"), "", ""))


def og_image(page):
    for pat in (
        r'<meta[^>]+property=["\']og:image["\'][^>]*content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]*property=["\']og:image["\']',
    ):
        m = re.search(pat, page, re.I)
        if m:
            return html.unescape(m.group(1)).strip()
    return ""


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; EiThiophile-image-fetcher/1.0)",
        "Accept-Language": "ja,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", "replace")


def main():
    with open(OWNED, encoding="utf-8") as f:
        raw = json.load(f)
    manual = raw if isinstance(raw, list) else (raw.get("manual") or [])
    images = {}
    if os.path.exists(OUT):
        try:
            with open(OUT, encoding="utf-8") as f:
                images = json.load(f).get("images", {})
        except Exception:
            images = {}

    urls = [(o or {}).get("url", "") for o in manual]
    if os.path.exists(DATA):
        try:
            with open(DATA, encoding="utf-8") as f:
                urls += [(r or {}).get("シナリオURL", "") for r in json.load(f)]
        except Exception:
            pass
    keys = []
    for u in urls:
        k = booth_key(u)
        if k and k not in keys:
            keys.append(k)

    todo = [k for k in keys if not images.get(k)]
    done = 0
    for k in todo[:MAX_FETCH]:
        try:
            img = og_image(fetch(k))
            if img:
                images[k] = img
                done += 1
            print(("OK  " if img else "NO  ") + k)
        except Exception as e:  # 取得できないものは次回また試す
            print("ERR " + k + " " + str(e))
        time.sleep(WAIT)

    images = {k: v for k, v in images.items() if k in keys}  # 消したURLは掃除
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"images": images}, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(f"取得 {done} 件 / 対象 {len(todo)} 件 / 登録済み {len(images)} 件")


if __name__ == "__main__":
    main()
