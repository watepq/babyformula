#!/usr/bin/env python3
"""从全量列表中筛选 1 段（0—6月龄）产品，按品牌聚合，找出表格未覆盖的主流品牌。"""
import json
import os
import re
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
data = json.load(open(os.path.join(RAW, "list_all.json")))
rows = data["rows"]
tab = json.load(open(os.path.join(RAW, "table_rows.json")))
tab_regs = {r["注册号"] for r in tab}

# 1段 = 产品名称/食品名称含 1段 或 0—6月龄（含 0-6、0~6 变体），排除 2段3段、特殊医学、调制
SEG = re.compile(r"[（(]\s*0\s*[—–~～\-]\s*6\s*月龄")


def is_stage1(r):
    name = (r.get("pfcpmc") or "") + (r.get("pfspmc") or "")
    return bool(SEG.search(name)) and "调制乳粉" not in name


s1 = [r for r in rows if is_stage1(r)]
valid = [r for r in s1 if r.get("zczzt") == "有效"]
print(f"总计 {len(rows)} 条；1段 {len(s1)} 条；其中有效 {len(valid)} 条")
print(f"状态分布: {json.dumps({k: sum(1 for r in s1 if r.get('zczzt')==k) for k in set(r.get('zczzt') for r in s1)}, ensure_ascii=False)}")

by_brand = defaultdict(list)
for r in valid:
    brand = (r.get("pftymc") or "").strip() or (r.get("qymcZw") or "")
    by_brand[brand].append(r)

# 表格中已覆盖的品牌/商标
covered = set()
for r in tab:
    o = next((x for x in rows if x["pfzcbh"] == r["注册号"]), None)
    if o:
        covered.add((o.get("pftymc") or "").strip())

# 主流品牌关键词（市场认知度高的进口/国产大厂）
MAINSTREAM = ["爱他美", " Aptamil", "美素", "Friso", "美赞臣", "Mead", "飞鹤", "星飞帆", "金领冠", "伊利",
              "君乐宝", "优萃", "雀巢", "NAN", "能恩", "启赋", "惠氏", "Wyeth", "雅培", "Similac", "合生元",
              "派星", "贝因美", "圣元", "优博", "蒙牛", "瑞哺恩", "雅士利", "美庐", "蓝河", "Blue River",
              "佳贝艾特", "Kabrita", "nanny", "羊", "a2", "至初", "海普诺凯", "Hyproca", "宜品", "朵拉小羊",
              "欧恩贝", "卡洛塔妮", "可瑞康", "Karicare", "Nutrilon", "诺优能", "牛栏", "Hero", "美可高特",
              "西谱", "御宝", "蓝天", "太子乐", "喜安智", "爱诺星", "素力高", "Sunloading", "安满", "安怡",
              "贝拉米", "Bellamy", "澳优", "能力多", "爱斯时光", "特维果", "喜宝", "Hipp", "乐乐雅", "惠氏"]

print("\n== 有效1段产品品牌（按产品数排序，前60）==")
for brand, rs in sorted(by_brand.items(), key=lambda kv: -len(kv[1]))[:60]:
    mark = "★表格已含" if brand in covered else ""
    hit = [m for m in MAINSTREAM if m.lower() in brand.lower()]
    if hit and not mark:
        mark = "☆主流未收录"
    print(f"{len(rs):3d}  {brand}  {mark}")

# 输出有效1段全量清单
json.dump(valid, open(os.path.join(RAW, "stage1_valid.json"), "w"), ensure_ascii=False, indent=1)
print("\nsaved stage1_valid.json")
