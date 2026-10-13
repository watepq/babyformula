# 婴幼儿配方奶粉注册配方数据库与对比工具

> 基于**国家市场监督管理总局「特殊食品信息查询平台」**公开注册数据（2490 条婴幼儿配方乳粉产品配方注册，全量、逐条、含营养成分表），提供成分亮点标注、证据分级、GB 法定带 + 国际参考带双层判定与多维对比的本地化查询工具。**零第三方依赖**（除 Excel 写回脚本外全部 Python 标准库），提供**静态单文件版**与 **SQLite 服务版**两种使用方式。

## ✨ 特性

- **全量官方数据**：2490 款注册配方 × 98,642 条成分记录（每100kJ/每100g 双口径），抓取自官方接口，非营销页面
- **两种使用方式**：
  - 🧊 **静态版** `web/standalone.html` —— 单文件 5.6MB，双击浏览器即开，无需任何服务（离线快照）
  - 🔁 **服务版** `server/server.py` —— SQLite 库存 + JSON API，配合抓取脚本可**增量刷新到最新注册数据**
- **成分亮点筛选**：21 项强化成分按**证据四级（必须/强/中/弱）**分组标注，赛道配色（肠道/免疫/视认/基础），悬停看文献级说明
- **双层参考带判定**（首要 → 次要）：
  - ✅ **国内 GB 法定带**：GB 10765/10766/10767-2021 原标准『每100kJ』区间直录（每段 25 项），原 PDF 留档仓库内
  - 🌐 **国际参考带**：Codex GSIF (CXS 72-1981)、ESPGHAN 2014、ENA 2020 follow-up、ENA/泰国 YCF 共识、EU 2016/127
- **批量勾选与对比**：列表页全选本页/全选结果，直接并排对比（成分对齐 + 差异高亮 + 双层判定行），最多 12 款
- **推荐发现**：口径完全可复现（1段 ∧ 有效 ∧ 未过期 ∧ 表格未收录 ∧ 主流品牌 → 187 款），非人为挑选
- **逐个遍历**：按筛选顺序逐款浏览配方全表 + 参考带判定 + 配方变更历史

## 🚀 快速开始

### 静态版（推荐第一次使用）

直接用浏览器打开：

```
web/standalone.html
```

全部数据内联在 HTML 内，不发起任何网络请求。数据为构建时快照（见页面标题栏日期）。

### 服务版（需要更新数据 / 二次开发时）

```bash
python3 server/build_db.py        # 从 data/raw/ 原始抓取重建 data/formula.db
python3 server/server.py          # http://127.0.0.1:8899  （PORT 环境变量可改端口）
python3 server/gen_standalone.py  # 重建静态版 web/standalone.html
```

仅用标准库（sqlite3 / http.server），Python ≥ 3.9 即可。

### 更新到最新注册数据（增量，断点续传）

```bash
python3 scripts/fetch_list_all.py      # 重抓列表 → data/raw/list_all.json
python3 scripts/fetch_details_all.py   # 只抓新增/缺失的详情 → data/raw/details_all.jsonl
python3 server/build_db.py             # 重建库存
python3 server/gen_standalone.py       # 刷新静态版快照
```

## 📁 目录结构

```
.
├── README.md / LICENSE / CHANGELOG.md / requirements.txt
├── web/
│   ├── index.html          # 服务版前端（5 视图单页）
│   └── standalone.html     # 静态单文件版（由 gen_standalone.py 生成，勿手改）
├── server/
│   ├── server.py           # 静态托管 + JSON API（/api/products、/api/limits 等 9 个端点）
│   ├── build_db.py         # 原始数据 → SQLite（成分标注/参考带/分层定义都在此）
│   └── gen_standalone.py   # 生成静态版（内联全量数据 + 本地 JS 数据层）
├── scripts/                # 数据抓取与核实脚本
│   ├── fetch_list_all.py / fetch_details_all.py / fetch_by_reg.py / fetch_recs.py
│   ├── diff_report.py      # Excel 27 行 vs 官方逐条比对
│   ├── analyze_stage1.py   # 1段有效池筛选
│   └── update_excel.py     # 核实结果写回 Excel（唯一需要 openpyxl 的脚本）
├── data/
│   ├── formula.db          # SQLite 库存（product/nutrient/limits/flag_def/meta）
│   └── raw/                # 官方接口原始返回（list_all.json、details_all.jsonl 等）
├── docs/
│   ├── 婴配粉核心成分功效证据分级调研结论.md   # 成分证据分级 + 各段参考带 + 结论
│   └── references/         # 查证材料留档：三部 GB 原 PDF+渲染图、PMC 表格摘录、EU 原文、PMID 索引
└── reports/
    └── 婴幼儿配方奶粉1段注册配方数据库（监管总局口径）.xlsx   # 核实回写后的 Excel
```

## 🔧 数据管道

```
官方接口(免鉴权) ──fetch_*──▶ data/raw/*.json(l) ──build_db──▶ data/formula.db
                                                                    │
                              web/index.html ◀──server.py───────────┤
                                                                    └──gen_standalone──▶ web/standalone.html
```

官方接口（GET 详情 / POST 列表，带 Referer 即可，详见 `docs/references/citations.md`）：
- `POST https://ypzsx.gsxt.gov.cn/specialfood_server/milkRecipeNew/queryHealthFood`
- `GET  https://ypzsx.gsxt.gov.cn/specialfood_server/milkRecipeNew/detailsHealthFood?id=`

## ⚖️ 判定口径说明

| 层 | 依据 | 定位 |
|---|---|---|
| 国内法定 | GB 10765-2021（1段）/ GB 10766-2021（2段较大婴儿）/ GB 10767-2021（3段幼儿），原表『每100kJ』列直录 | **首要依据**。注册审评即按此，超法定上限属数据异常应复核 |
| 国际参考 | Codex GSIF / ESPGHAN 2014 / ENA 2020 / YCF 共识 / EU 2016/127（每100kcal÷4.184 换算） | **次要参考**。严于 GB 属正常（如维D：GB 0.48–1.20 µg/100kJ vs ESPGHAN ≤0.60），『高于参考上限』≠违规 |

成分功效证据四级：**必须**（国际基本必需项）/ **强**（系统综述或荟萃支持）/ **中**（RCT 方向一致但数量少）/ **弱**（机制或间接证据为主）。详见 [docs/婴配粉核心成分功效证据分级调研结论.md](docs/婴配粉核心成分功效证据分级调研结论.md)。

## ⚠️ 免责声明

- 原始数据来自政府公开信息，本仓库仅作技术性整理与留档，不对其准确性作超出来源的保证；以监管总局官网为准。
- Codex 原 PDF（FAO 内网需登录）无法直接抓取时，采用同行评审综述（PMC8620542 / PMC10180831）的转载值，均已在页面与文档标注出处链。
- 本项目为信息整理与文献综述，**不构成医疗建议**；婴儿喂养方案请遵儿科医生指导。母乳优先。

## License

代码：[MIT](LICENSE)。数据与文献摘录：遵循各自来源的公开条款（政府公开信息 / PMC 开放获取），本仓库不对其主张版权。
