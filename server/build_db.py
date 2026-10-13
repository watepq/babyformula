#!/usr/bin/env python3
"""构建配方奶粉 SQLite 库存。
数据源（可重复运行、增量刷新）：
  data/raw/list_all.json          全量2490条列表（基本信息）
  data/raw/details_all.jsonl      已抓取的详情（含营养成分 elments）
  data/raw/official_by_reg.json   表格27行详情
  data/raw/recommend_details.json 推荐候选详情
输出：data/formula.db
"""
import html
import json
import os
import re
import sqlite3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "data", "raw")
DBDIR = os.path.join(ROOT, "data")
DB = DBDIR + "/formula.db"
TODAY = "2026-10-12"
SRC = "https://ypzsx.gsxt.gov.cn/specialfood/#/food"


def c(s):
    if s is None:
        return ""
    s = html.unescape(str(s))
    for t in ("<sup>", "</sup>", "<sub>", "</sub>", "️"):
        s = s.replace(t, "")
    return " ".join(s.split())


def dt(s):
    return c(s)[:10]


def stage_of(name):
    n = name or ""
    if re.search(r"0\s*[—–~～\-]\s*6\s*月龄", n):
        return 1
    if re.search(r"6\s*[—–~～\-]\s*12\s*月龄", n):
        return 2
    if re.search(r"12\s*[—–~～\-]\s*36\s*月龄", n):
        return 3
    if "1段" in n:
        return 1
    if "2段" in n:
        return 2
    if "3段" in n:
        return 3
    return 0


SCHEMA = """
DROP TABLE IF EXISTS product;
DROP TABLE IF EXISTS nutrient;
DROP TABLE IF EXISTS meta;
DROP TABLE IF EXISTS flag_def;
DROP TABLE IF EXISTS limits;
CREATE TABLE product(
  reg TEXT PRIMARY KEY, infoshar_id TEXT, brand TEXT, product_name TEXT,
  food_name TEXT, product_name_en TEXT, company TEXT, company_en TEXT,
  legal_rep TEXT, address TEXT, approve_date TEXT, valid_until TEXT,
  process TEXT, country TEXT, status TEXT, remark TEXT, change_log TEXT,
  stage INTEGER, is_goat INTEGER, in_table INTEGER, is_recommended INTEGER,
  detail_fetched INTEGER, n_nutrients INTEGER DEFAULT 0,
  flags TEXT, is_mainstream INTEGER DEFAULT 0, is_expired INTEGER DEFAULT 0);
CREATE TABLE nutrient(
  reg TEXT, seq INTEGER, name TEXT, unit TEXT, per_100kj TEXT, per_100g TEXT);
CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE flag_def(name TEXT PRIMARY KEY, category TEXT, tier TEXT, evidence TEXT, effect TEXT);
CREATE TABLE limits(
  nutrient TEXT, basis TEXT, min_v REAL, max_v REAL, unit TEXT, source TEXT,
  stage INTEGER DEFAULT 1, kind TEXT DEFAULT 'intl');
CREATE INDEX idx_stage ON product(stage, status);
CREATE INDEX idx_brand ON product(brand);
CREATE INDEX idx_nreg ON nutrient(reg);
CREATE INDEX idx_nname ON nutrient(name);
"""

# —— 成分亮点：从营养成分表项目名称判定（官方注册标签列示）——
# 分类/证据等级/功效 依据《婴配粉核心成分功效证据分级调研结论.md》+ 本次补充检索（2026-10-12）
# category: 肠道 / 免疫 / 视认 / 基础
# evidence: 强 / 中 / 弱-中 / 弱 / 中偏强 / 基础必需
FLAG_RULES = [
    # name, matcher, category, evidence, 功效一句
    ("乳铁蛋白", lambda s: "乳铁蛋白" in s, "免疫", "中", "免疫/减少感染；剂量敏感(≥100mg/100mL 才对标临床)"),
    ("OPO", lambda s: "二油酸" in s and "棕榈酸甘油三酯" in s, "肠道", "强", "sn-2棕榈酸：软化大便、减少钙皂、促钙吸收(EFSA背书)"),
    ("HMO", lambda s: "岩藻糖基乳糖" in s or "乳糖-n-新四糖" in s or "hmo" in s, "肠道", "强/中", "真HMO(2'-FL/LNnT)：菌群母乳化+安全强证据，防病中等"),
    ("益生元GOS", lambda s: "低聚半乳糖" in s, "肠道", "强", "增殖双歧杆菌、软化大便；剂量需达研究用量(~0.8g/100mL)"),
    ("益生元FOS", lambda s: "低聚果糖" in s or "多聚果糖" in s or "聚葡萄糖" in s, "肠道", "强", "与GOS 9:1组合证据最强；单独FOS亦属益生元"),
    ("DHA", lambda s: "dha" in s or "二十二碳六烯酸" in s, "视认", "强(视觉)/弱(认知)", "视觉敏锐度有荟萃强证据；智商获益未证实；各款含量趋同"),
    ("ARA", lambda s: "ara" in s or "aa/ara" in s or "二十碳四烯酸" in s, "视认", "强(视觉)", "与DHA配对；Codex要求ARA≥DHA"),
    ("MFGM乳脂球膜", lambda s: "乳脂球膜" in s or "mfgm" in s, "免疫", "中偏强", "认知+减少感染方向一致，试验总数少；常以稀奶油/磷脂来源标示"),
    ("核苷酸", lambda s: "核苷酸" in s, "免疫", "中", "改善疫苗抗体应答等免疫指标；硬终点有限；≤10.8mg/100kcal"),
    ("叶黄素", lambda s: "叶黄素" in s, "视认", "弱-中", "黄斑色素/脑类胡萝卜素；机制明确，婴儿RCT极少"),
    ("CPP", lambda s: "酪蛋白磷酸肽" in s, "基础", "弱-中", "结合矿物质助锌铁吸收；体外/动物为主"),
    ("益生菌", lambda s: "双歧杆菌" in s or "乳杆菌" in s or "杆菌b" in s or ("发酵" in s and "菌" in s) or "益生菌" in s, "肠道", "中", "Bb-12/M-16V等：菌群终点证据好；硬临床终点间接；中耳炎NMA有支持"),
    ("骨桥蛋白", lambda s: "骨桥蛋白" in s or "osteopontin" in s or "opn" in s, "免疫", "弱-中", "OPN：2024专家组认为安全+功能线索；RCT少"),
    ("神经节苷脂", lambda s: "神经节苷脂" in s or ("唾液酸" in s and "苷" in s), "视认", "弱", "认知/抗感染机制研究为主，婴儿RCT有限"),
    ("α-乳白蛋白", lambda s: "α-乳白蛋白" in s or "乳白蛋白" in s, "基础", "中", "高质量乳清蛋白：低蛋白配方+改善喂养耐受/夜间喂养RCT(2025/2026)"),
    ("乳清蛋白", lambda s: "乳清蛋白" in s, "基础", "中", "蛋白来源结构优化：高乳清比例使酪蛋白/乳清比接近母乳；证据与α-乳白蛋白同源"),
    ("磷脂", lambda s: "磷脂" in s, "视认", "弱-中", "MFGM相关组分；来源多为大豆/蛋黄"),
    ("牛磺酸", lambda s: "牛磺酸" in s, "基础", "基础必需", "母乳天然存在；国际专家参考上限12mg/100kcal；加多无额外证据"),
    ("胆碱", lambda s: "胆碱" in s, "基础", "基础必需", "条件必需；参考7–150mg/100kcal区间；高下无临床差异证据"),
    ("肌醇", lambda s: "肌醇" in s, "基础", "基础必需", "参考4–40mg/100kcal区间(ESPGHAN)"),
    ("左旋肉碱", lambda s: "肉碱" in s, "基础", "基础必需", "脂肪代谢必需；参考≥1.2mg/100kcal"),
]

# —— 证据四级分层（网页筛选条按此分组）——
# 必须=国际基本必需项(基础必需) / 强=系统综述或荟萃支持 / 中=方向一致但RCT少 / 弱=机制或间接证据为主
# 归层规则：中偏强→中；弱-中→弱(取保守)
TIER_OF = {
    "乳铁蛋白": "中", "OPO": "强", "HMO": "强", "益生元GOS": "强", "益生元FOS": "强",
    "DHA": "强", "ARA": "强", "MFGM乳脂球膜": "中", "核苷酸": "中", "叶黄素": "弱",
    "CPP": "弱", "益生菌": "中", "骨桥蛋白": "弱", "神经节苷脂": "弱", "α-乳白蛋白": "中",
    "乳清蛋白": "中", "磷脂": "弱", "牛磺酸": "必须", "胆碱": "必须", "肌醇": "必须",
    "左旋肉碱": "必须",
}

# —— 主流品牌白名单（市场认知度高；命中即视为“主流”，用于推荐口径）——
MAINSTREAM = ["爱他美", "aptamil", "诺优芮", "诺优能", "牛栏", "可瑞康", "karicare",
              "nutrilon", "美素佳儿", "美素力", "friso", "美赞臣", "蓝臻", "铂睿",
              "飞鹤", "星飞帆", "飞帆", "臻爱", "金领冠", "伊利", "塞纳牧", "君乐宝",
              "优萃", "恬适", "雀巢", "能恩", "超启", "早瑞", "瑞铂", "启赋", "惠氏",
              "铂臻", "爱儿乐", "雅培", "恩美力", "菁挚", "合生元", "派星", "贝塔星",
              "贝因美", "圣元", "优博", "a2", "至初", "蓝河", "佳贝艾特", "kabrita",
              "喜宝", "hipp", "海普诺凯", "能立多", "荷致", "瑞哺恩", "蒙牛", "雅士利",
              "完达山", "光明", "贝拉米", "bellamy", "朵拉小羊", "欧恩贝", "宜品",
              "蓓康僖", "和氏", "美羚", "西谱", "红星", "欧贝星", "蓝盾"]


def flags_of(els, det):
    """匹配范围：营养成分表名称 + 产品名 + 备注 + 配方变更历史
    （活菌/磷脂/OPN/神经节苷脂等只出现在配料表或变更史，官方API不返回配料表）"""
    s = " ".join(c(e.get("xm")) for e in els).lower()
    extra = (c(det.get("pfcpmc")) + c(det.get("bz")) + c(det.get("bglsjl"))).lower()
    both = s + " " + extra
    out = []
    for name, fn, *_rest in FLAG_RULES:
        try:
            if fn(s) or (name in ("益生菌", "MFGM乳脂球膜", "骨桥蛋白", "神经节苷脂", "磷脂", "α-乳白蛋白", "乳清蛋白")
                        and fn(extra)):
                out.append(name)
        except Exception:  # noqa: BLE001
            pass
    return out


# —— 权威参考带（per 100kJ；由核查过的 per 100kcal 值 ÷4.184 换算）——
# source 标注数字出处；"参考上限/下限"指国际专家共识或Codex文件（非中国强制注册门槛，
# 中国产品法定依据是 GB 10765-2021，注册审评即按该标准，故"超标"仅相对国际参考带而言）
# nutrient 名称用与前端约定的键；判定所取的成分名匹配模式在 judge 里处理
LIMITS = [
    # (nutrient, basis, min, max, unit_per100kJ, source, stage)
    # —— 1段（0–6月）：ESPGHAN 2014 / Codex GSIF / GB 10765-2021（PMC8620542 Table1, PMC10180831 Table5）——
    ("蛋白质", "Codex GSIF (CXS 72-1981)", 1.8 / 4.184, 3.0 / 4.184, "g", "PMC8620542 Table2 (LASPGHAN综述引Codex)", 1),
    ("脂肪", "Codex GSIF (CXS 72-1981)", 4.4 / 4.184, 6.0 / 4.184, "g", "PMC8620542 Table2", 1),
    ("亚油酸", "Codex GSIF", 0.3 / 4.184 * 1000, 1.4 / 4.184 * 1000, "mg", "PMC10180831 Table5 (LA GUL 1400mg/100kcal)", 1),
    ("α-亚麻酸", "Codex GSIF", 50 / 4.184, None, "mg", "PMC10180831 Table5 (≥50mg/100kcal)", 1),
    ("DHA", "Codex GSIF (GUL)", None, 22 / 4.184, "mg", "PMC10180831 Table5 脚注: ≤0.5%FA≈22mg/100kcal 且 ARA≥DHA", 1),
    ("DHA", "GB 10765-2021", 15 / 4.184, 40 / 4.184, "mg", "PMC10180831 Table5 中国列 15–40mg/100kcal", 1),
    ("ARA", "GB 10765-2021", None, 80 / 4.184, "mg", "PMC10180831 Table5 中国列 ≤80mg/100kcal", 1),
    ("胆碱", "ESPGHAN 参考", 7 / 4.184, 50 / 4.184, "mg", "PMC8620542 Table1 (ESPGHAN 2014 IF: 7–50mg/100kcal)", 1),
    ("左旋肉碱", "ESPGHAN 参考下限", 1.2 / 4.184, None, "mg", "PMC8620542 Table1 (≥1.2mg/100kcal)", 1),
    ("肌醇", "ESPGHAN 参考", 4 / 4.184, 40 / 4.184, "mg", "PMC8620542 Table1 (4–40mg/100kcal)", 1),
    ("维生素D", "ESPGHAN/Codex 参考", 1 / 4.184, 2.5 / 4.184, "µg", "PMC8620542 Table1 (1–2.5µg/100kcal)", 1),
    ("铁", "ESPGHAN 参考(牛奶基1段)", 0.3 / 4.184, 1.3 / 4.184, "mg", "PMC8620542 Table1 (0.3–1.3mg/100kcal)", 1),
    ("锌", "ESPGHAN 参考", 0.5 / 4.184, 1.5 / 4.184, "mg", "PMC8620542 Table1 (0.5–1.5mg/100kcal)", 1),
    ("碘", "ESPGHAN 参考", 10 / 4.184, 50 / 4.184, "µg", "PMC8620542 Table1 (10–50µg/100kcal)", 1),
    # —— 2段（6–12月）：ENA follow-up（Fewtrell 2020 共识, PMC8620542 Table3）+ EU 2016/127 法定 ——
    ("蛋白质", "ENA follow-up 参考", 1.7 / 4.184, 2.5 / 4.184, "g", "PMC8620542 Table3 (ENA/ESPGHAN 2020 FUF)", 2),
    ("蛋白质", "EU (EU)2016/127 法定", 1.8 / 4.184, 2.5 / 4.184, "g", "eu_2016_127 AnnexII: 0.43–0.6 g/100kJ", 2),
    ("脂肪", "ENA follow-up 参考", 4.4 / 4.184, 6.0 / 4.184, "g", "PMC8620542 Table3", 2),
    ("亚油酸", "ENA follow-up(GUL)", 0.3 / 4.184 * 1000, 1.4 / 4.184 * 1000, "mg", "PMC8620542 Table3 (LA 0.3g–GUL1.4g)", 2),
    ("α-亚麻酸", "ENA follow-up", 50 / 4.184, None, "mg", "PMC8620542 Table3 (≥50mg/100kcal)", 2),
    ("铁", "ENA follow-up(牛奶基)", 1.1 / 4.184, 1.9 / 4.184, "mg", "PMC8620542 Table3 (1.1–1.9mg/100kcal): 6月后铁需求升高", 2),
    ("铁", "EU (EU)2016/127 法定", 0.6 / 4.184, 2.0 / 4.184, "mg", "eu_2016_127 AnnexII FOF: 0.6–2.0mg/100kcal", 2),
    ("维生素D", "ENA follow-up(GUL)", 1 / 4.184, 4.5 / 4.184, "µg", "PMC8620542 Table3 (1–4.5µg/100kcal)", 2),
    ("胆碱", "ENA follow-up(GUL)", 7 / 4.184, 150 / 4.184, "mg", "PMC8620542 Table3 (7–GUL150mg/100kcal)", 2),
    ("牛磺酸", "ENA follow-up 参考上限", None, 12 / 4.184, "mg", "PMC8620542 Table3 (≤12mg/100kcal)", 2),
    ("核苷酸", "ENA follow-up(GUL)", None, 10.8 / 4.184, "mg", "PMC8620542 Table3 (总添加核苷酸≤GUL10.8)", 2),
    ("左旋肉碱", "ENA follow-up 下限", 1.2 / 4.184, None, "mg", "PMC8620542 Table3 (≥1.2mg/100kcal)", 2),
    ("锌", "ENA follow-up(GUL)", 0.5 / 4.184, 1.5 / 4.184, "mg", "PMC8620542 Table3 (0.5–GUL1.5)", 2),
    ("钙", "ENA follow-up 下限", 50 / 4.184, None, "mg", "PMC8620542 Table3 (≥50, GUL180)", 2),
    # —— 3段（12–36月）：ENA/泰国营养学会 YCF 共识（PMC8620542 Table4, 原文引[21]）——
    ("蛋白质", "ENA/泰国 YCF 共识", 1.6 / 4.184, 2.7 / 4.184, "g", "PMC8620542 Table4 (1.6–2.7g/100kcal)", 3),
    ("脂肪", "ENA/泰国 YCF 共识", 4.4 / 4.184, 6.0 / 4.184, "g", "PMC8620542 Table4", 3),
    ("亚油酸", "ENA/泰国 YCF 共识", 500 / 4.184, None, "mg", "PMC8620542 Table4 (≥500mg/100kcal)", 3),
    ("α-亚麻酸", "ENA/泰国 YCF 共识", 50 / 4.184, None, "mg", "PMC8620542 Table4 (≥50mg/100kcal)", 3),
    ("DHA", "YCF 共识(≥0.3%总脂)", 15 / 4.184, None, "mg", "PMC8620542 Table4: ≥0.3%fat≈15mg/100kcal(按5g脂肪折算)", 3),
    ("铁", "YCF 共识(GUL)", 1.0 / 4.184, 3.0 / 4.184, "mg", "PMC8620542 Table4 (≥1, GUL3 mg/100kcal)", 3),
    ("钙", "YCF 共识下限", 200 / 4.184, None, "mg", "PMC8620542 Table4 (≥200mg/100kcal)", 3),
    ("维生素D", "YCF 共识(GUL)", 1.5 / 4.184, 4.5 / 4.184, "µg", "PMC8620542 Table4 (≥1.5, GUL4.5µg)", 3),
    ("锌", "YCF 共识(GUL)", 0.6 / 4.184, 1.8 / 4.184, "mg", "PMC8620542 Table4 (≥0.6, GUL1.8)", 3),
    ("碘", "YCF 共识(GUL)", 12 / 4.184, 36 / 4.184, "µg", "PMC8620542 Table4 (≥12, GUL36µg)", 3),
    ("钠", "YCF 共识(GUL)", 25 / 4.184, 75 / 4.184, "mg", "PMC8620542 Table4 (≥25, GUL75)", 3),
]


# —— 国内法定参考带 GB（首要判定依据；数值直接取自国标原表“每100kJ”列，与库存单位一致，无需换算）——
def _gb(stage, rows):
    std = {1: "GB 10765-2021", 2: "GB 10766-2021", 3: "GB 10767-2021"}[stage]
    return [(n, std + " 法定", lo, hi, u,
             "GB原标准表(每100kJ) 留档 docs/references/" + std + ".pdf", stage, "domestic")
            for n, lo, hi, u in rows]


LIMITS = _gb(1, [
    ("蛋白质", 0.43, 0.72, "g"), ("脂肪", 1.05, 1.43, "g"), ("亚油酸", 70, 330, "mg"),
    ("α-亚麻酸", 12, None, "mg"), ("碳水化合物", 2.2, 3.3, "g"),
    ("维生素A", 14, 36, "µg"), ("维生素D", 0.48, 1.20, "µg"), ("维生素E", 0.12, 1.20, "mg"),
    ("维生素K", 0.96, 6.45, "µg"), ("维生素C", 2.4, 16.7, "mg"),
    ("胆碱", 4.8, 23.9, "mg"), ("钠", 7, 14, "mg"), ("钾", 17, 43, "mg"),
    ("钙", 12, 35, "mg"), ("磷", 6, 24, "mg"), ("镁", 1.2, 3.6, "mg"),
    ("铁", 0.10, 0.36, "mg"), ("锌", 0.12, 0.36, "mg"), ("碘", 3.6, 14.1, "µg"),
    ("硒", 0.72, 2.06, "µg"), ("肌醇", 1.0, 9.6, "mg"), ("牛磺酸", 0.8, 4.0, "mg"),
    ("左旋肉碱", 0.3, None, "mg"), ("DHA", 3.6, 9.6, "mg"), ("ARA", None, 19.1, "mg"),
]) + _gb(2, [
    ("蛋白质", 0.43, 0.84, "g"), ("脂肪", 0.84, 1.43, "g"), ("亚油酸", 70, 330, "mg"),
    ("α-亚麻酸", 12, None, "mg"), ("碳水化合物", 2.2, 3.3, "g"),
    ("维生素A", 18, 43, "µg"), ("维生素D", 0.48, 1.20, "µg"), ("维生素E", 0.14, 1.20, "mg"),
    ("维生素K", 0.96, 6.45, "µg"), ("维生素C", 2.4, 16.7, "mg"),
    ("胆碱", 4.8, 23.9, "mg"), ("钠", None, 20, "mg"), ("钾", 18, 54, "mg"),
    ("钙", 17, 43, "mg"), ("磷", 8, 26, "mg"), ("镁", 1.2, 3.6, "mg"),
    ("铁", 0.24, 0.48, "mg"), ("锌", 0.12, 0.36, "mg"), ("碘", 3.6, 14.1, "µg"),
    ("硒", 0.48, 2.06, "µg"), ("肌醇", 1.0, 9.6, "mg"), ("牛磺酸", 0.8, 4.0, "mg"),
    ("左旋肉碱", 0.3, None, "mg"), ("DHA", 3.6, 9.6, "mg"), ("ARA", None, 19.1, "mg"),
]) + _gb(3, [
    ("蛋白质", 0.43, 0.96, "g"), ("脂肪", 0.84, 1.43, "g"), ("亚油酸", 70, 330, "mg"),
    ("α-亚麻酸", 12, None, "mg"), ("碳水化合物", 1.8, 3.6, "g"),
    ("维生素A", 18, 43, "µg"), ("维生素D", 0.48, 1.20, "µg"), ("维生素E", 0.14, 1.20, "mg"),
    ("维生素K", 0.96, 6.45, "µg"), ("维生素C", 2.4, 16.7, "mg"),
    ("胆碱", 4.8, 23.9, "mg"), ("钠", None, 20, "mg"), ("钾", 18, 69, "mg"),
    ("钙", 17, 50, "mg"), ("磷", 8, 26, "mg"), ("镁", 1.4, 4.3, "mg"),
    ("铁", 0.24, 0.60, "mg"), ("锌", 0.10, 0.31, "mg"), ("碘", 1.4, 14.1, "µg"),
    ("硒", 0.48, 2.06, "µg"), ("肌醇", 1.0, 9.6, "mg"), ("牛磺酸", 0.8, 4.0, "mg"),
    ("左旋肉碱", 0.3, None, "mg"), ("DHA", None, 9.6, "mg"), ("ARA", None, 19.1, "mg"),
]) + LIMITS


# 判定用的成分名匹配（营养成分表 xm 名称 → limits 键）
JUDGE_PATTERNS = {
    "蛋白质": lambda n: n == "蛋白质",
    "脂肪": lambda n: n == "脂肪",
    "亚油酸": lambda n: n == "亚油酸",
    "α-亚麻酸": lambda n: n.startswith("α-亚麻酸") or n == "α亚麻酸",
    "DHA": lambda n: "dha" in n.lower() or "二十二碳六烯酸" in n,
    "ARA": lambda n: "ara" in n.lower() or "aa/ara" in n or "二十碳四烯酸" in n,
    "胆碱": lambda n: n == "胆碱",
    "牛磺酸": lambda n: n == "牛磺酸",
    "左旋肉碱": lambda n: "肉碱" in n,
    "核苷酸": lambda n: "核苷酸" in n,
    "肌醇": lambda n: n == "肌醇" or "myo-肌醇" in n,
    "维生素D": lambda n: n.startswith("维生素D"),
    "铁": lambda n: n == "铁",
    "钙": lambda n: n == "钙",
    "锌": lambda n: n == "锌",
    "碘": lambda n: n == "碘",
    "钠": lambda n: n == "钠",
    "磷脂": lambda n: "磷脂" in n,
    "维生素A": lambda n: n.startswith("维生素A"),
    "维生素E": lambda n: n.startswith("维生素E"),
    "维生素K": lambda n: n.startswith("维生素K"),
    "维生素C": lambda n: n.startswith("维生素C"),
    "钾": lambda n: n == "钾",
    "磷": lambda n: n == "磷",
    "镁": lambda n: n == "镁",
    "硒": lambda n: n == "硒",
    "碳水化合物": lambda n: n == "碳水化合物" or n.startswith("碳水化合物"),
}


def is_mainstream(row, brand):
    s = (c(row.get("pftymc")) + c(row.get("pfcpmc")) + c(row.get("qymcZw"))
         + c(brand)).lower()
    return any(m in s for m in MAINSTREAM)


def load_details():
    """reg -> detail dict"""
    d = {}
    p = DIR + "/details_all.jsonl"
    if os.path.exists(p):
        with open(p) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    if r.get("found") and r.get("detail"):
                        d[r["pfzcbh"]] = r["detail"]
                except Exception:  # noqa: BLE001
                    pass
    p = DIR + "/official_by_reg.json"
    if os.path.exists(p):
        for reg, v in json.load(open(p)).items():
            if v.get("detail"):
                d[reg] = v["detail"]
    p = DIR + "/recommend_details.json"
    if os.path.exists(p):
        for reg, det in json.load(open(p)).items():
            if det:
                d[reg] = det
    return d


def main():
    os.makedirs(DBDIR, exist_ok=True)
    rows = json.load(open(DIR + "/list_all.json"))["rows"]
    details = load_details()

    tab_regs = set()
    tp = DIR + "/table_rows.json"
    if os.path.exists(tp):
        tab_regs = {r["注册号"] for r in json.load(open(tp))}
    rec_regs = set()
    rp = DIR + "/recommend_picks.json"
    if os.path.exists(rp):
        rec_regs = {r["注册号"] for r in json.load(open(rp))}

    conn = sqlite3.connect(DB)
    conn.executescript(SCHEMA)

    for r in rows:
        reg = r.get("pfzcbh")
        det = details.get(reg) or {}
        merged = {**r, **{k: v for k, v in det.items() if k != "elments"}}
        pname = c(merged.get("pfcpmc"))
        fname = c(merged.get("pfspmc"))
        fetched = 1 if det else 0
        els = (det.get("elments") or []) if det else []
        vuntil = dt(merged.get("yxqz"))
        expired = 1 if (vuntil and vuntil < TODAY and c(merged.get("zczzt")) == "有效") else 0
        conn.execute(
            """INSERT OR REPLACE INTO product(reg,infoshar_id,brand,product_name,
               food_name,product_name_en,company,company_en,legal_rep,address,
               approve_date,valid_until,process,country,status,remark,change_log,
               stage,is_goat,in_table,is_recommended,detail_fetched,n_nutrients,
               flags,is_mainstream,is_expired)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (reg, det.get("infosharId") or r.get("infosharId"),
             c(merged.get("pftymc")), pname, fname, c(merged.get("pfcpmcYw")),
             c(merged.get("qymcZw")), c(merged.get("qymcYw")), c(merged.get("fddbr")),
             c(merged.get("scdz")), dt(merged.get("pzrq")), vuntil,
             c(merged.get("scgy")), c(merged.get("gsszgdqzw")), c(merged.get("zczzt")),
             c(merged.get("bz")), c(merged.get("bglsjl")), stage_of(pname + fname),
             1 if "羊" in (pname + fname) else 0,
             1 if reg in tab_regs else 0, 1 if reg in rec_regs else 0,
             fetched, len(els), ",".join(flags_of(els, det)),
             1 if is_mainstream(r, c(merged.get("pftymc"))) else 0, expired),
        )
        conn.execute("DELETE FROM nutrient WHERE reg=?", (reg,))
        seen_n = set()
        for e in els:
            nm = c(e.get("xm"))
            key = (nm, c(e.get("kjhl")), c(e.get("khl")))
            if key in seen_n:
                continue
            seen_n.add(key)
            conn.execute(
                "INSERT INTO nutrient VALUES(?,?,?,?,?,?)",
                (reg, int(e.get("xh") or 0), nm, c(e.get("dw")),
                 c(e.get("kjhl")), c(e.get("khl"))),
            )
    conn.commit()
    # —— 数据来源元信息（供网页“数据来源说明”展示）——
    meta = {
        "source": "国家市场监督管理总局 · 特殊食品信息查询平台（婴幼儿配方乳粉产品配方注册）",
        "source_url": SRC,
        "as_of": TODAY,
        "api_list": "POST /milkRecipeNew/queryHealthFood  （列表，含注册号/企业/工艺/状态/有效期）",
        "api_detail": "GET  /milkRecipeNew/detailsHealthFood?id=  （详情，含营养成分表 elments）",
        "pipeline": "①列表接口全量翻页25页→list_all.json ②按 infosharId 逐条抓详情→details_all.jsonl（断点续传）③合并表格27行+推荐候选详情 ④清洗HTML标签/成分名→入库",
        "table_basis": "『表格已收录』= 原 Excel『注册总览』27 行，逐条按注册号回官方复核，差异见 Excel『官方核实差异』",
        "recommend_basis": "『推荐』口径 = 1段 且 状态有效 且 未过期 且 表格未收录 且 命中主流品牌白名单；可复现，见 build_db.py MAINSTREAM",
        "nutrient_note": "成分明细仅对已抓详情的产品可见；后台仍在增量下载，重跑 build_db.py 即可补全",
    }
    conn.executemany("INSERT OR REPLACE INTO meta VALUES(?,?)", list(meta.items()))
    conn.executemany("INSERT OR REPLACE INTO flag_def VALUES(?,?,?,?,?)",
                     [(n, cat, TIER_OF.get(n, "中"), ev, eff) for n, _f, cat, ev, eff in FLAG_RULES])
    def _lm(r):
        r = tuple(r)
        return r if len(r) == 8 else r + ("intl",)
    conn.executemany("INSERT OR REPLACE INTO limits VALUES(?,?,?,?,?,?,?,?)", [_lm(r) for r in LIMITS])
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM product").fetchone()[0]
    nf = conn.execute("SELECT COUNT(*) FROM product WHERE detail_fetched=1").fetchone()[0]
    nn = conn.execute("SELECT COUNT(*) FROM nutrient").fetchone()[0]
    s1 = conn.execute("SELECT COUNT(*) FROM product WHERE stage=1").fetchone()[0]
    s1v = conn.execute("SELECT COUNT(*) FROM product WHERE stage=1 AND status='有效'").fetchone()[0]
    conn.close()
    print(f"DB -> {DB}\nproduct={n} (detail_fetched={nf}) nutrient_rows={nn}\nstage1={s1} stage1_有效={s1v}")


if __name__ == "__main__":
    main()
