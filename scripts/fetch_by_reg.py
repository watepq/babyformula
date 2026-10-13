#!/usr/bin/env python3
"""从监管总局特殊食品信息查询平台按配方注册号逐条抓取官方注册信息。"""
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
OUT = os.path.join(RAW, "official_by_reg.json")


def req(url, data=None, tries=4):
    for i in range(tries):
        try:
            r = urllib.request.Request(
                url,
                data=json.dumps(data).encode() if data is not None else None,
                headers=HDRS,
            )
            with urllib.request.urlopen(r, timeout=60) as f:
                return json.loads(f.read().decode("utf-8", "replace"))
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"  retry {i+1} {type(e).__name__}: {e}\n")
            time.sleep(2 + 3 * i)
    return None


def query(zcbh):
    return req(
        BASE + "/milkRecipeNew/queryHealthFood",
        {"currentPage": 1, "pageSize": 10, "pfcpmc": "", "pfzcbh": zcbh,
         "qymcZw": "", "pfspmc": ""},
    )


def detail(infoshar_id):
    return req(BASE + f"/milkRecipeNew/detailsHealthFood?id={infoshar_id}")


def main():
    regs = json.load(open(os.path.join(RAW, "regs.json")))
    result = {}
    for i, reg in enumerate(regs, 1):
        sys.stderr.write(f"[{i}/{len(regs)}] {reg}\n")
        q = query(reg)
        rows = (q or {}).get("data", {}).get("list") or []
        rec = None
        for r in rows:
            if r.get("pfzcbh") == reg:
                rec = r
                break
        if rec is None and rows:
            rec = rows[0]
        if rec is None:
            result[reg] = {"found": False, "query": q}
            sys.stderr.write("   !! 未命中\n")
            time.sleep(1.2)
            continue
        det = detail(rec.get("infosharId"))
        d = (det or {}).get("data") or {}
        result[reg] = {"found": True, "list": rec, "detail": d}
        sys.stderr.write(f"   ok {d.get('pfcpmc')} | 状态={d.get('zczzt')} | 成分={len(d.get('elments') or [])}\n")
        time.sleep(1.0)
        json.dump(result, open(OUT, "w"), ensure_ascii=False, indent=1)
    json.dump(result, open(OUT, "w"), ensure_ascii=False, indent=1)
    print("done", len(result), "->", OUT)


if __name__ == "__main__":
    main()
