# 数据来源与历史/预测拼接方案

政策版本以 `config/research_policy.json` 为准，本土来源注册表为 `config/country_sources.json`；公开来源矩阵同时标注配置优先来源、回退来源与限制，配置不代表当前报告已可用。

## 研究单元与主来源

| 研究单元 | 历史基础库 | 当前产量预测 | 官方 Actual | 独立参考 |
|---|---|---|---|---|
| Global | USDA PSD 修订后估计 | 各国家本土优先、PSD 回退的产量组合 | 尚无完整官方终值序列 | PSD / WASDE 供需表 |
| 东南亚（按作物固定成员） | USDA PSD 同一成员集合历史估计 | 固定成员本土优先组合 | 不将 Estimate 改称 Actual | PSD 供需表 |
| 海外国家 | USDA PSD | 本土来源有可比成对值则采用，否则两年回退 PSD | 有官方明确证据再单列接入 | PSD / WASDE / CropWatch 独立序列 |
| 中国 | PSD MY 修订估计；NBS CY 实产独立展示 | 玉米/大豆/糖优先 CASDE，小麦优先 CropWatch；水稻因精米转换未验证回退 PSD | NBS 已有覆盖 | 农业展望长期预测 |

历史复盘默认采用 `local_composite` 产量，历史部分仍保留 PSD 修订估计的身份，不能当作事件当年的可得预测。PSD/WASDE 库存、消费和供需表是独立参考，不用本土组合产量拼成同源供需表。

**不使用邻国作为替代数据。** 每个成员用本国记录；地区求和只用本地区真实成员。同一个数据库覆盖多个国家，并不是拿一个国家数值代替另一个国家。

## 东南亚固定成员

| 作物 | 成员 | 汇总口径 |
|---|---|---|
| wheat | 不设汇总项：入选生产规模不足 | 本土优先、PSD 回退；产量求和 |
| corn | Thailand, Vietnam, Indonesia, Philippines, Burma, Laos, Cambodia | 本土优先、PSD 回退；产量求和 |
| rice | Thailand, Vietnam, Indonesia, Philippines, Burma, Laos, Cambodia, Malaysia | 本土优先、PSD 回退；精米 |
| soybean | Indonesia, Burma | 本土优先、PSD 回退；产量求和 |
| sugar | Thailand, Vietnam, Indonesia, Philippines, Burma | 本土优先、PSD 回退；产量求和 |

## 小产量剔除规则

香港、澳门、新加坡、文莱、东帝汶不进入研究层，已下载原始记录仍归档。马来西亚只保留达到门槛的水稻，不保留零产量糖/玉米/大豆。
基于已归档 PSD 2020–2024 五个完整年份的平均产量，固定入选门槛：小麦/玉米/水稻 ≥0.5 Mt、大豆 ≥0.1 Mt、糖 ≥0.25 Mt。这是产品研究范围的判断标准，不是统计显著性标准。证据见 `docs/research_universe_evidence.json`。
成员名单随政策版本手工审查调整，不跟随每日数据自动改变。历史回看沿用当前固定研究范围，不能据此声称是当时已知的成分选择或无偏回测。

## 数据如何衔接

首页当前优先展示同源成对同比：只有某个国家本年和上年都存在同一本土主来源、相同产品定义和明确年度映射时，才同时替换 PSD 的两个国家组件。缺少任一侧时，两年都回退 PSD，禁止用本土本年值除以 PSD 上年值。页面同时保留 PSD 全球同比和百分点差。

已注册的本土预测来源包括中国 CASDE/CropWatch、加拿大 AAFC、巴西 CONAB、澳大利亚 ABARES、印度 DA&FW、南非 CEC、欧盟 EC、阿根廷 BCR 和乌克兰 UGA。源站无法访问、报告未提供完整成对值或产品定义不兼容时，注册存在但组合自动回退 PSD，并保留原因。中国稻谷尚未取得经审核的精米转换，继续使用 PSD 精米。

1. 历史基础库：PSD 已修订历史 Estimate（通常1960起）；每次下载记录快照可得日期，不伪装成当年实时预测。
2. 国家预测：本土来源可比成对值优先；缺少本年/上年任一侧或定义、年度映射未验证，两年同时回退 PSD。PSD 当前/前一市场年度的 Forecast 是保守年份分类，可能包含暂定估计；WASDE 历史月报不冒充 PSD 旧快照。
3. 中国：CASDE 玉米/大豆/糖、CropWatch 小麦按作物注册；NBS Actual、农业展望长期预测各自保留。稻谷与精米、冬小麦与全年小麦、早稻/半晚稻与全年稻谷分别保存，未验证口径不得组合。
4. 地区与全球：按成员分别选择同源本年/上年对，再加总两年的产量。组合允许不同国家采用各自来源，但同一国家两年不跨源；保留各成员来源和回退原因。固定成员缺失不缩小样本；Global 剔除 EU 成员重复，不再次计入地区汇总。
5. 地区同比 = 本年总产量 / 上年同成员总产量 − 1；等价于以上年产量为权重的成员增长，不平均各国同比。单产用总产量/总面积，稻谷单产不能由精米产量计算。
6. MY是各成员市场年度起始年对齐，并非所有国家同一自然年收获；地区进出口为成员毛额，包含内部贸易，不能视为地区对外贸易。
7. 跨机构均值默认关闭。只有同产品、同地区、同年度口径、同单位且45天内至少两家独立机构时，才可在对照区看共识；主序列不采用均值，PSD 回退按成对规则明确标注。
8. 没有数据就保留N/A。禁止插值、借邻国产量、按比例分摊省级或拼接不兼容口径。

## 各作物入选国家

| 作物 | 国家（均用本国数据；预测本土优先、PSD 回退） |
|---|---|
| wheat | China, United States, Brazil, Argentina, India, European Union, Russia, Ukraine, Australia, Canada, Mexico, South Africa, Kazakhstan, Paraguay, Bangladesh, Pakistan, Turkey, Japan, United Kingdom |
| corn | China, United States, Brazil, Argentina, India, European Union, Russia, Ukraine, Canada, Thailand, Vietnam, Mexico, South Africa, Kazakhstan, Paraguay, Indonesia, Bangladesh, Philippines, Pakistan, Turkey, Korea, North, Burma, Laos, Cambodia |
| rice | China, United States, Brazil, Argentina, India, European Union, Russia, Thailand, Vietnam, Paraguay, Indonesia, Bangladesh, Philippines, Pakistan, Turkey, Japan, Korea, South, Korea, North, Taiwan, Burma, Laos, Cambodia, Malaysia |
| soybean | China, United States, Brazil, Argentina, India, European Union, Russia, Ukraine, Canada, Mexico, South Africa, Kazakhstan, Paraguay, Indonesia, Bangladesh, Turkey, Japan, Korea, South, Korea, North, Burma |
| sugar | China, United States, Brazil, Argentina, India, European Union, Russia, Ukraine, Australia, Thailand, Vietnam, Mexico, South Africa, Indonesia, Philippines, Pakistan, Turkey, Japan, Burma, United Kingdom |

## 代码与自动更新

```mermaid
flowchart LR
  A[research_policy.json] --> B[分源抓取与不可变归档]
  B --> C[DuckDB Actual / Estimate / Forecast]
  C --> D[同源规范化与固定成员汇总]
  A --> D
  D --> E[校验 / JSON API / Parquet]
  E --> F[Next.js / GitHub Pages]
```

- `policy.py`：配置校验、研究名单、主来源及公开来源矩阵。
- `regions.py`：完整同快照地区求和、成员证据与缺失控制。
- `research.py`：原始记录→规范国家名→Global→地区→研究范围→输出；Global先算，绝不把地区再加进去。
- `outlook.py`：当前值选择与同比；`scheduler.py`：按配置挑选到期任务。
- `update_forecasts.py`：每日预测检查入口；`update_all.py --group all` 用于手动全源维护，`--group build` 仅重建。
- GitHub Actions 每日北京时间 14:17（06:17 UTC）运行 `python scripts/update_forecasts.py` 检查预测来源，同日已检查者跳过。基础历史产量、NOAA 气候观测与价格库手动维护；农业预测检查不代表气候预测或每天发布新报告。失败保留原数据与错误状态，下次重试。
- Actions先恢复便携库，运行统一入口，检查 publication_complete 后提交数据并部署确切提交；校验/JSON/Parquet任一步失败不部署。源站单项失败但既有数据校验通过时允许发布Stale状态。
- 静态 `/api/policy.json` 与动态 `/api/policy` 是同一来源矩阵；`/api/outlook/rice?view=regions` 默认地区，`view=countries` 下钻国家。

`write_policy_docs.py` 生成独立 `SOURCE_MATRIX.md` 配置矩阵，不覆盖本文件的审定方法。修改配置后依次执行 `python scripts/write_policy_docs.py`、`python scripts/update_all.py --group build`、`npm run build`。
