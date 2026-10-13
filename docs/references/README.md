# 参考资料索引（查证材料留档 docs/references/）

> 用途：所有"国际参考带判定"与调研结论的**原始出处留档**，避免重复联网抓取。
> 建档日期：2026-10-12。终端 curl 对多数站点被 Cloudflare/白名单拦截，凡标注"浏览器提取"的材料均经 Playwright 页面 DOM 抓取后落盘，属全文/全表级证据。

## 文件清单

| 文件 | 内容 | 获取方式 |
|---|---|---|
| `pmc8620542_tables.md` | JPGN 2021 拉美共识：Table1 ESPGHAN **1段**、Table3 ENA **2段(follow-up)**、Table4 ENA/泰国 **3段(YCF 12–36月)**、Table5 能量/蛋白小结 + 关键正文句 | 浏览器提取 PMC 页面 DOM（全文） |
| `eu_2016_127_fulltext.txt` | 欧盟条例 (EU) 2016/127（IF+FOF 组成要求+标签）全文纯文本，67.6KB | 浏览器提取 EUR-Lex（curl 返回 0 字节，被 bot 拦截） |
| `eu_2016_127_annexII.txt` | 上者 Annex II 组成要求切片：FOF 蛋白 0.43–0.6 g/100kJ(=1.8–2.5 g/100kcal)、FOF 铁 0.6–2.0、大豆 FOF 铁 0.9–2.5 mg/100kcal 等，含每100kJ 与每100kcal 双列 | 同上（Python 切片） |
| `citations.md` | 各成分文献 PMID 锚点、Codex/FAO 访问障碍记录、GB 国标检索 API 用法 | 会话内检索汇总 |
| `GB10765-2021.pdf` + `gb65-*.png` | **GB 10765-2021 婴儿配方食品（1段）原标准 PDF**（闽清县政府网转载国家食品安全风险评估中心公开文本）；字体加密无文本层，已用 pdftoppm 逐页渲染，表1–4 经视觉读取入库 | curl 直下 ✅ |
| `GB10766-2021.pdf` + `gb66-*.png` | **GB 10766-2021 较大婴儿配方食品（2段）**，同上 | curl 直下 ✅ |
| `GB10767-2021.pdf` + `gb67-*.png` | **GB 10767-2021 幼儿配方食品（3段）**，同上 | curl 直下 ✅ |

## 数据流对应关系

- `_db/build_db.py` LIMITS（1段判定） ← pmc8620542_tables.md Table1 + citations.md（PMC10180831 Table5 GB/Codex 列）
- `_db/build_db.py` LIMITS（待加的 2/3 段判定） ← Table3（2段）/ Table4（3段）+ eu_2016_127_annexII.txt（2段 EU 法定）
- 《婴配粉核心成分功效证据分级调研结论.md》"4R 参考带"章节 ← 以上全部

## 已知访问障碍（勿重复试错）

- **Codex CXS 72-1981 / CXS 156-1987 原 PDF**：`workspace.fao.org`（FAO Sharepoint，需账号登录）。曾尝试 `/api/savepdf` 落盘，得到的是挑战页 HTML（35KB, 非 PDF），无效。
- **pmc.ncbi.nlm.nih.gov**：终端 curl 与 fetch_webpage 均触发 PoW/cookie 挑战；**浏览器直读可行**。
- **europepmc.org**：REST 接口在本网络 DNS 解析失败（Cloudflare 1016 Origin DNS error）。
- **eur-lex.europa.eu**：curl 0 字节；浏览器直读可行。
- **web.archive.org / duckduckgo / sppt.cfsamr.gov.cn**：不可达。
- **std.samr.gov.cn（全国标准信息公共服务平台）**：✅ 可用！`POST https://std.samr.gov.cn/gb/search/gbQueryPage`，表单字段 `searchText`、`pageNumber`、`pageSize`，返回 JSON（现行/废止状态齐全）。openstd.samr.gov.cn 亦通。
  - 注意：URL 带 query 参数会 404，必须 POST 表单；中文参数用 `--data-urlencode`。

## 待办关联

- ~~2/3 段 GB 法定值~~ ✅ 已完成：三部 GB 原 PDF 已下载留档并视觉读取入 limits（kind='domestic'，网页双层判定：GB 首要+国际次要）。⚠注：**2021 版编号 GB 10766=2段、GB 10767=3段**（与直觉相反）；GB 维D 法定带 0.48–1.20 µg/100kJ（2010 旧版为 0.25–1.0，已修正）。
- ⚠ 1 段国际带遗留：胆碱已修正为 ESPGHAN 7–50；铁行 mg 换算 bug 已修。
