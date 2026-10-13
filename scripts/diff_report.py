#!/usr/bin/env python3
"""对比表格 27 行与官方接口返回，生成差异清单。"""
import html
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OFF = json.load(open(os.path.join(RAW, "official_by_reg.json")))
TAB = json.load(open(os.path.join(RAW, "table_rows.json")))


def clean(s):
    if s is None:
        return ""
    s = html.unescape(str(s))
    return " ".join(s.split())


def d(s):
    return clean(s)[:10]


diffs = []
for row in TAB:
    reg = row["注册号"]
    o = OFF.get(reg)
    rec = {"注册号": reg, "系列": row["系列"], "diffs": []}
    if not o or not o.get("found"):
        rec["diffs"].append(("整条", "表格有", "官方平台查无此注册号（可能注销/变更）"))
        diffs.append(rec)
        continue
    det = o["detail"]
    pairs = [
        ("产品名称", row["产品名称"], det.get("pfcpmc")),
        ("注册状态", row["注册状态"], det.get("zczzt")),
        ("批准日期", row["批准日期"], d(det.get("pzrq"))),
        ("有效期至", row["有效期至"], d(det.get("yxqz"))),
        ("生产企业", row["生产企业"], det.get("qymcZw")),
        ("原产国", row["原产国"], det.get("gsszgdqzw")),
        ("生产工艺", row["工艺"], det.get("scgy")),
    ]
    for name, tv, ov in pairs:
        tv, ov = clean(tv), clean(ov)
        if tv in ("—", "", "None"):
            tv = ""
        if ov in ("—", "", "None"):
            ov = ""
        if name == "原产国" and (ov, tv) in (("中国", "中国"),):
            continue
        if tv != ov:
            # 产品名称含®等标记，做宽松包含判断
            if name == "产品名称" and (ov.replace("®", "").replace(" ", "") in tv.replace("®", "").replace(" ", "") or tv.replace("®", "").replace(" ", "") in ov.replace("®", "").replace(" ", "")):
                continue
            rec["diffs"].append((name, tv or "(空)", ov or "(空)"))
    rec["official"] = {
        "pfcpmc": clean(det.get("pfcpmc")), "zczzt": clean(det.get("zczzt")),
        "pzrq": d(det.get("pzrq")), "yxqz": d(det.get("yxqz")),
        "qymcZw": clean(det.get("qymcZw")), "gsszgdqzw": clean(det.get("gsszgdqzw")),
        "scgy": clean(det.get("scgy")), "spmc": clean(det.get("pfspmc")),
        "pftymc": clean(det.get("pftymc")),
        "bz": clean(det.get("bz")), "n_elements": len(det.get("elments") or []),
        "bglsjl": clean(det.get("bglsjl")),
    }
    diffs.append(rec)

out = [r for r in diffs if r["diffs"]]
print(f"共 {len(diffs)} 条，有差异 {len(out)} 条\n")
for r in out:
    print(f"== {r['注册号']} {r['系列']}")
    for name, tv, ov in r["diffs"]:
        print(f"   {name}: 表格=[{tv}] 官方=[{ov}]")
json.dump(diffs, open(os.path.join(RAW, "diff_report.json"), "w"), ensure_ascii=False, indent=1)
