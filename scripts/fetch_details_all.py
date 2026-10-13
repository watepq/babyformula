#!/usr/bin/env python3
"""全量抓取『婴幼儿配方乳粉产品配方注册』2490 条详情（含营养成分表 elments）。
逐行写入 details_all.jsonl，已存在的 id 自动跳过（断点续传）。"""
import json
import os
import sys
import time
import urllib.request

BASE = "https://ypzsx.gsxt.gov.cn/specialfood_server"
HDRS = {
    "Referer": "https://ypzsx.gsxt.gov.cn/specialfood/",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
}
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "data", "raw")
OUT = DIR + "/details_all.jsonl"


def get(url, tries=5):
    for i in range(tries):
        try:
            r = urllib.request.Request(url, headers=HDRS)
            with urllib.request.urlopen(r, timeout=90) as f:
                return json.loads(f.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"  retry {i+1}: {e}\n")
            time.sleep(2 + 3 * i)
    return None


def main():
    rows = json.load(open(DIR + "/list_all.json"))["rows"]
    done = set()
    if os.path.exists(OUT):
        with open(OUT) as f:
            for line in f:
                try:
                    done.add(json.loads(line)["id"])
                except Exception:  # noqa: BLE001
                    pass
    sys.stderr.write(f"total={len(rows)} already={len(done)}\n")
    n_ok = n_fail = 0
    with open(OUT, "a") as f:
        for i, r in enumerate(rows, 1):
            rid = r.get("infosharId")
            if not rid or rid in done:
                continue
            d = get(BASE + f"/milkRecipeNew/detailsHealthFood?id={rid}")
            data = (d or {}).get("data")
            rec = {"id": rid, "pfzcbh": r.get("pfzcbh"), "found": bool(data),
                   "detail": data}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            if data:
                n_ok += 1
            else:
                n_fail += 1
            if i % 25 == 0:
                sys.stderr.write(f"[{i}/{len(rows)}] ok={n_ok} fail={n_fail}\n")
            time.sleep(0.25)
    print(f"details done ok={n_ok} fail={n_fail} -> {OUT}")


if __name__ == "__main__":
    main()
