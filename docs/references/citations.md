# 文献与出处锚点（会话检索留档, 2026-10-12）

## 成分功效证据（详见《婴配粉核心成分功效证据分级调研结论.md》）

| 主题 | 锚点 | 备注 |
|---|---|---|
| OPO sn-2 棕榈酸 | EFSA NDA Panel 2014（2011.0214 委托）结论：足月健康婴儿软化大便/减少钙皂 | 证据"强" |
| GOS/FOS 9:1 | Moro 2002（J Nutr）+ ESPGHAN 共识 | 剂量 ~0.8 g/100mL |
| HMO 2'-FL | Berger 2020 综述; Tiranathanagul 2021 RCT | 安全+菌群强，防病中 |
| DHA 视觉 | 科克伦 BMJ 2016 综述（Gould 2013 等） | 视觉强/认知弱 |
| MFGM | Timby 2015 RCT（神经发育）; Neururer/ENA 综述 | 中偏强 |
| 乳铁蛋白 | Granot 2014（早产儿败血症）; Griffiths 2019 剂量反应 | 中，剂量敏感 |
| A2 β-酪蛋白 | He 2015 等 | 中（耐受性） |
| 核苷酸 | Jagadeesh 2013 综述（疫苗抗体应答） | 中 |
| 叶黄素 | Cuthbert 2020 RCT（脑类胡萝卜素） | 弱-中 |
| CPP | 体外/动物为主 | 弱-中 |
| **骨桥蛋白 OPN** | PMID **38919388**（Nutr Rev 2024 专家组安全+功能）; PMID **37299387**（Adv Nutr 2023 Sørensen） | 弱-中 |
| **神经节苷脂** | PMID **42395632**（2026 MFGM 综述，机制为主） | 弱 |
| **益生菌 Bb-12** | PMID **42491017**（中耳炎 NMA 2026）; PMID **42540473**（新生儿 RCT 2026）; PMID **41800422**（Bb-12 系统综述 2026）; PMID **42038244**（LF+Bb-12 2026） | 中 |
| **α-乳白蛋白** | PMID **40910342**（低蛋白高α-LA 免疫 RCT 2025）; PMID **42095870**（夜间喂养 RCT 2026） | 中 |
| 胆碱（母体摄入→胎脑） | Obeid 2022 Adv Nutr 荟萃（doi 10.1093/advances/nmac065） | 基础必需 |

## 参考带（法定/共识）数值出处

| 用途 | 出处 | 状态 |
|---|---|---|
| 1段 Codex GSIF 必需区间 | CXS 72-1981（2023 合并版）原 PDF | ❌ workspace.fao.org 需登录，未落盘；数值取 PMC10180831 Table5 / PMC8620542 转载 |
| 1段 GB 10765-2021 | PMC10180831 Table5 中国列（DHA 15–40、ARA ≤80、LA 0.3–1.4 mg/g、ALA ≥50 mg 等，每100kcal） | ✅ 已入 LIMITS |
| 1段 ESPGHAN 2014 | PMC8620542 **Table 1**（见 pmc8620542_tables.md） | ✅ 全文落盘 |
| 2段 ENA follow-up | PMC8620542 **Table 3**（原文引 [20]=Fewtrell 2020 ESPGHAN-JPGN consensus） | ✅ 全文落盘 |
| 2段 EU 法定 | (EU) 2016/127 Annex II（FOF 蛋白 1.8–2.5、铁 0.6–2.0 mg/100kcal 等） | ✅ 全文落盘 eu_2016_127_*.txt |
| 3段 YCF 共识 | PMC8620542 **Table 4**（原文引 [21]=泰国营养学会/ENA 2018 consensus, JPGN） | ✅ 全文落盘 |
| 3段 GB 10766-2021 / 2段 GB 10767-2021 | 国标文本 | ⏳ 仅确认 std.samr 检索通道可用，限量表未落盘 |

## 官方数据接口（本项目主数据源）

- 列表：`POST https://ypzsx.gsxt.gov.cn/specialfood_server/milkRecipeNew/queryHealthFood`（免鉴权，Referer+UA 即可）
- 详情：`GET  https://ypzsx.gsxt.gov.cn/specialfood_server/milkRecipeNew/detailsHealthFood?id=<infosharId>`
- 国标检索：`POST https://std.samr.gov.cn/gb/search/gbQueryPage`（searchText/pageNumber/pageSize 表单）

## 失败/放弃的抓取路径（勿重复尝试）

- Codex PDF 直下（FAO Sharepoint 登录墙）→ 改走 PMC 转载
- europepmc REST（DNS 1016）→ 改走 PMC 浏览器
- web.archive / duckduckgo / sppt.cfsamr.gov.cn（网络不可达）
- curl 抓 pmc/eur-lex（Cloudflare PoW/0字节）→ 浏览器提取
