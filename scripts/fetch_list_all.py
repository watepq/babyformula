#!/usr/bin/env python3
"""全量下载特殊食品信息查询平台『婴幼儿配方乳粉产品配方注册』列表（2490 条）。"""
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

BASE = "https://ypzsx.gsxt.gov.cn/specialfood_server"
HDRS = {
    "Content-Type": "application/json",
    "Referer": "https://ypzsx.gsxt.gov.cn/specialfood/",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
}
OUT = os.path.join(RAW, "list_all.json")


def post(path, data, tries=5):
    for i in range(tries):
        try:
            r = urllib.request.Request(BASE + path, data=json.dumps(data).encode(), headers=HDRS)
            with urllib.request.urlopen(r, timeout=90) as f:
                return json.loads(f.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"  retry {i+1}: {e}\n")
            time.sleep(2 + 3 * i)
    raise RuntimeError("failed: " + path)


def main():
    first = post("/milkRecipeNew/queryHealthFood",
                 {"currentPage": 1, "pageSize": 100, "pfcpmc": "", "pfzcbh": "",
                  "qymcZw": "", "pfspmc": ""})
    total = first["data"]["count"]
    pages = (total + 99) // 100
    rows = list(first["data"]["list"])
    sys.stderr.write(f"total={total} pages={pages}\n")
    for p in range(2, pages + 1):
        d = post("/milkRecipeNew/queryHealthFood",
                 {"currentPage": p, "pageSize": 100, "pfcpmc": "", "pfzcbh": "",
                  "qymcZw": "", "pfspmc": ""})
        rows.extend(d["data"]["list"])
        sys.stderr.write(f"page {p}/{pages} cum={len(rows)}\n")
        time.sleep(0.8)
    # 去重（防翻页期间数据漂移）
    seen, uniq = set(), []
    for r in rows:
        k = r.get("pfzcbh") + "|" + r.get("infosharId", "")
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    json.dump({"count": total, "fetched": len(rows), "rows": uniq},
              open(OUT, "w"), ensure_ascii=False, indent=1)
    print("saved", len(uniq), "rows ->", OUT)


if __name__ == "__main__":
    main()
