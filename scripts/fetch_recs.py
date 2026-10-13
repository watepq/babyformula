#!/usr/bin/env python3
"""定向抓取推荐候选18条 + 尚未含成分的表格行的详情，用于成分亮点分析。"""
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "data", "raw")

BASE = "https://ypzsx.gsxt.gov.cn/specialfood_server"
HDRS = {"Referer": "https://ypzsx.gsxt.gov.cn/specialfood/",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124"}


def get(url, tries=5):
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(r, timeout=90) as f:
                return json.loads(f.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"  r{i+1}:{e}\n")
            time.sleep(2 + 3 * i)
    return None


def main():
    # 从 list_all 拿到注册号->infosharId 映射
    idx = {r["pfzcbh"]: r["infosharId"] for r in json.load(open(DIR + "/list_all.json"))["rows"]}
    picks = json.load(open(DIR + "/recommend_picks.json"))
    out = {}
    for p in picks:
        reg = p["注册号"]
        rid = idx.get(reg)
        if not rid:
            sys.stderr.write(f"no id {reg}\n")
            continue
        d = get(BASE + f"/milkRecipeNew/detailsHealthFood?id={rid}")
        out[reg] = (d or {}).get("data")
        sys.stderr.write(f"{reg} elments={len((out[reg] or {}).get('elments') or [])}\n")
        time.sleep(0.4)
    json.dump(out, open(DIR + "/recommend_details.json", "w"), ensure_ascii=False, indent=1)
    print("saved", len(out))


if __name__ == "__main__":
    main()
