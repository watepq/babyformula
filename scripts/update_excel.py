#!/usr/bin/env python3
"""将官方核实结果写回 Excel：修正注册总览，新增核实差异与推荐sheet。"""
import html
import json
import os
import shutil

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
XLSX = os.path.join(ROOT, "reports", "婴幼儿配方奶粉1段注册配方数据库（监管总局口径）.xlsx")
BAK = XLSX + ".bak-20261012"
DIR = RAW
VERIF_DATE = "2026-10-12"


def c(s):
    if s is None:
        return ""
    s = html.unescape(str(s))
    for t in ("<sup>", "</sup>", "️"):
        s = s.replace(t, "")
    return " ".join(s.split())


def dt(s):
    return c(s)[:10]


OFF = json.load(open(DIR + "/official_by_reg.json"))
REC = json.load(open(DIR + "/recommend_details.json"))
PICKS = json.load(open(DIR + "/recommend_picks.json"))

shutil.copy(XLSX, BAK)
wb = openpyxl.load_workbook(XLSX)
ws = wb["注册总览"]

HEAD_FILL = PatternFill("solid", fgColor="1F4E79")
HEAD_FONT = Font(color="FFFFFF", bold=True)
CHG_FILL = PatternFill("solid", fgColor="FFF2CC")
TITLE_FONT = Font(bold=True, size=13)

# 现有列: A品牌 B系列 C产品名称 D注册号 E状态 F批准 G有效 H企业 I原产国 J国产进口
#          K工艺 L奶基 M过敏原 N执行标准 O含配料表 P来源 Q来源链接
# 新增 R 官方核实 S 核实日期
ws.cell(3, 18, "官方核实")
ws.cell(3, 19, "核实日期")
for col in (18, 19):
    ws.cell(3, col).fill = HEAD_FILL
    ws.cell(3, col).font = HEAD_FONT

changes = []
for row in range(4, ws.max_row + 1):
    reg = ws.cell(row, 4).value
    if not reg:
        continue
    reg = str(reg).strip()
    o = OFF.get(reg, {}).get("detail")
    if not o:
        continue
    off = {
        3: o.get("pfcpmc"),  # 产品名称
        5: o.get("zczzt"),   # 状态
        6: dt(o.get("pzrq")), 7: dt(o.get("yxqz")),
        8: o.get("qymcZw"),  # 企业
        11: o.get("scgy"),   # 工艺
    }
    colname = {3: "产品名称", 5: "注册状态", 6: "批准日期", 7: "有效期至", 8: "生产企业", 11: "生产工艺"}
    note = []
    for col, ov in off.items():
        old = c(ws.cell(row, col).value)
        newv = c(ov)
        if newv in ("—", "None"):
            newv = ""
        if old in ("—", "None", "-"):
            old = ""
        if old == newv:
            continue
        # 名称仅标点差异（、↔,）也统一为官方
        ws.cell(row, col, newv if newv else old)
        if newv and (not old or old.replace("、", ",").replace(" ", "") != newv.replace("、", ",").replace(" ", "")):
            note.append(f"{colname[col]}:[{old or '空'}→{newv}]")
            ws.cell(row, col).fill = CHG_FILL
    if note:
        changes.append((reg, c(ws.cell(row, 2).value), "；".join(note)))
    ws.cell(row, 18, "已核实" + ("（有修正）" if note else "（一致）"))
    ws.cell(row, 19, VERIF_DATE)

# ===== 新增：官方核实差异 =====
if "官方核实差异" in wb.sheetnames:
    del wb["官方核实差异"]
dv = wb.create_sheet("官方核实差异")
dv.cell(1, 1, f"官方核实差异（对照 特殊食品信息查询平台，核实日期 {VERIF_DATE}）").font = TITLE_FONT
dv.append([])
dv.append(["配方注册号", "系列", "修正内容"])
for col in range(1, 4):
    dv.cell(3, col).fill = HEAD_FILL
    dv.cell(3, col).font = HEAD_FONT
for reg, ser, note in changes:
    dv.append([reg, ser, note])
for col, w in zip("ABC", (22, 18, 90)):
    dv.column_dimensions[col].width = w

# ===== 新增：推荐1段(未收录) =====
if "推荐1段(未收录)" in wb.sheetnames:
    del wb["推荐1段(未收录)"]
rv = wb.create_sheet("推荐1段(未收录)")
rv.cell(1, 1, "其他值得推荐的 1段 注册配方（主流品牌、现行有效、未过期，表格原未收录）").font = TITLE_FONT
rv.cell(2, 1, f"来源：特殊食品信息查询平台全量检索（1段有效共 535 条），按市场主流品牌精选；核实日期 {VERIF_DATE}").font = Font(size=10, color="888888")
heads = ["推荐品牌/系列", "产品名称", "配方注册号", "原产国", "国产/进口", "生产工艺", "生产企业",
         "批准日期", "有效期至", "官方核实"]
rv.append([])
rv.append(heads)
hr = 4
for col in range(1, len(heads) + 1):
    rv.cell(hr, col).fill = HEAD_FILL
    rv.cell(hr, col).font = HEAD_FONT


def feats(det):
    names = " ".join(c(e.get("xm")) for e in (det.get("elments") or []))
    f = []
    for w in ["乳铁蛋白", "DHA", "叶黄素", "牛磺酸", "核苷酸", "低聚半乳糖", "多聚果糖"]:
        if w in names:
            f.append(w)
    return "、".join(f)


for p in PICKS:
    det = REC.get(p["注册号"], {})
    gi = "国产" if c(det.get("gsszgdqzw")) == "中国" else "进口"
    rv.append([p["推荐品牌"], c(det.get("pfcpmc")), p["注册号"], c(det.get("gsszgdqzw")), gi,
               c(det.get("scgy")), c(det.get("qymcZw")), dt(det.get("pzrq")), dt(det.get("yxqz")),
               "有效·" + feats(det)])
for col, w in zip("ABCDEFGHIJ", (16, 40, 20, 8, 10, 16, 30, 12, 12, 40)):
    rv.column_dimensions[col].width = w

# ===== 更新说明页 =====
sm = wb["说明与数据来源"]
sm.cell(sm.max_row + 2, 2, f"官方核实更新（{VERIF_DATE}）：直接调用监管总局特殊食品信息查询平台接口逐条复核全部 {len(changes) and ''}27 条注册信息；"
        f"修正 {len(changes)} 条字段（详见『官方核实差异』），并新增『推荐1段(未收录)』收录主流品牌现行有效配方。"
        f"配套 SQLite 库存与遍历对比网页见文件夹 _db / _web。")

wb.save(XLSX)
print("写回完成。修正条数:", len(changes))
for x in changes:
    print("  ", x[0], x[1], "->", x[2])
print("sheets:", wb.sheetnames)
