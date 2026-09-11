# 数据来源与历史/预测拼接方案

政策版本以 `config/research_policy.json` 为准，本土来源注册表为 `config/country_sources.json`。预测选择的统一原则是：**有本国预测数据用本国预测数据，无则用PSD。** 配置不代表对应年度已有可用报告。

## 研究单元与主来源

| 研究单元 | 历史基础库 | 当前产量预测 | 官方实产 | 独立参考 |
|---|---|---|---|---|
| Global | USDA PSD 修订后估计 | 按成员国家采用本国预测或 PSD 的产量组合 | 尚无完整官方终值序列 | PSD / WASDE 供需表 |
| 东南亚（按作物固定成员） | USDA PSD 同一成员集合历史估计 | 固定成员按本国预测或 PSD 选择 | 有官方明确证据再单列接入 | PSD 供需表 |
| 海外国家 | USDA PSD | 有可用本国预测时采用本国预测，否则使用 PSD | 有官方明确证据再单列接入 | PSD / WASDE / CropWatch 独立序列 |
| 中国 | PSD MY 修订估计；NBS CY 实产独立保存 | 玉米/大豆/糖优先 CASDE，小麦优先 CropWatch；水稻精米转换未验证时使用 PSD | NBS 已有覆盖 | 农业展望长期预测 |

历史复盘默认读取 `actual_production` 真实产量数据库，不使用预测或估计历史填补空缺。PSD/WASDE 库存、消费和供需表是独立参考，不与真实产量拼成同源供需表。

**不使用邻国作为替代数据。** 每个成员用本国记录；地区求和只用本地区真实成员。

## 东南亚固定成员

| 作物 | 成员 | 汇总口径 |
|---|---|---|
| wheat | 不设汇总项：入选生产规模不足 | 不适用 |
| corn | Thailand, Vietnam, Indonesia, Philippines, Burma, Laos, Cambodia | 按成员选择，产量求和 |
| rice | Thailand, Vietnam, Indonesia, Philippines, Burma, Laos, Cambodia, Malaysia | 按成员选择，精米 |
| soybean | Indonesia, Burma | 按成员选择，产量求和 |
| sugar | Thailand, Vietnam, Indonesia, Philippines, Burma | 按成员选择，产量求和 |

## 数据如何衔接

巴西玉米、大豆、小麦采用 CONAB 全国调查。每日从报告目录发现最新工作簿，按各作物生产量列的年度表头解析：夏粮的 2025/26 与小麦的 2026 不作同年处理。只有报告覆盖所选年度时才采用，未发布的下一季使用 PSD。阿根廷采用 BCR GEA 全国报告，读取报告日期、当季明确产量预测及上季产量表；正常气候中心预测与更高产量情景不混用。解析规则变化时，数据库事务替换该文档的当前解释，原文件与历次解析快照继续保留。

1. 历史基础库：PSD 已修订历史 Estimate（通常1960起）；每次下载记录快照可得日期，不伪装成当年实时预测。
2. 国家预测：有可用本国预测时采用本国预测，无可用本国预测时使用 PSD。同比只在本年、上年来源与产品口径可比时计算，不跨来源计算同比。
3. 真实产量：仅从 `actual_production` 读取有官方明确证据的终值。FAOSTAT 提供全球与中国小麦、玉米、稻谷、大豆的年度官方数据；NBS 提供中国最新终值。没有记录即显示 N/A，不插值、不借邻国数据、不改用预测值。
4. 地区与全球：按成员选择当年产量后加总。固定成员缺失不缩小样本；Global 剔除 EU 成员重复，不再次计入地区汇总。
5. MY是各成员市场年度起始年对齐，并非所有国家同一自然年收获；地区进出口为成员毛额，包含内部贸易，不能视为地区对外贸易。
6. 跨机构均值默认关闭。只有同产品、同地区、同年度口径、同单位且45天内至少两家独立机构时，才可在对照区看共识；主序列不采用均值。
7. 没有数据就保留N/A。禁止插值、借邻国产量、按比例分摊省级或拼接不兼容口径。
8. 首页“预测同比范围”是两套来源预测同比之间的来源差异范围，不是统计置信区间；“产量缺口”按两套全球预测的产量差额除以基准产量计算。正值代表缺口扩大并标红，负值代表缺口收窄并标绿。

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
- `research.py`：原始记录→规范国家名→Global→地区→研究范围→输出；Global先算，绝不把地区再加进去。
- `event_study.py`：历史复盘默认读取真实产量库；PSD/WASDE仅作供需参考。
- `update_forecasts.py`：每日预测检查入口；`update_all.py --group all` 用于手动全源维护，`--group build` 仅重建。
- GitHub Actions 每日北京时间 14:17（06:17 UTC）运行 `python scripts/update_forecasts.py` 检查预测来源。FAOSTAT、NBS 等基础历史产量、NOAA 气候观测与价格库手动维护。

`write_policy_docs.py` 生成 `SOURCE_MATRIX.md`。修改配置后依次执行 `python scripts/write_policy_docs.py`、`python scripts/update_all.py --group build`、`npm run build`。
