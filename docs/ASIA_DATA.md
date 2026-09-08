# 东亚与东南亚数据接续

> 本文件是前一轮“补国家”的审计记录。当前已改为地区优先、按作物筛选有效生产者，并统一海外PSD主序列；最新执行方案见 [DATA_STITCHING.md](DATA_STITCHING.md)，下方19国等旧统计不再代表当前研究名单。

## 已确认的根因

1. USDA 已抓取完整来源国家，但 `COUNTRIES` 白名单未包含日本、朝韩、缅甸、柬埔寨、老挝、马来西亚等；这些记录在构建网站 JSON 时被过滤。
2. 世界地图采用 Myanmar / South Korea / North Korea，USDA 使用 Burma / Korea, South / Korea, North，原先没有匹配。
3. PSD 将当前/前一市场年度保守标记为 Forecast，旧同比只接受上年 Estimate，因此有两年数量也显示 N/A。不能通过把 Forecast 改称 Actual 来消除此缺口。
4. CropWatch 2026 表头、单位与载体变化导致漏解析；国家摘要与省级季节作物不可简单互换。

## 数据合同

- `scripts/geography.py` 维护规范国家ID、原始来源名称映射、地图名称和 East Asia / Southeast Asia 分组，覆盖19个国家/地区；原始库记录不改名，JSON额外保留 `source_country`。
- `scripts/outlook.py` 在后端生成 `comparisons.reported/estimate/actual`。每个比较保留上年数量、类型、目标年、来源、口径、原始URL和可得日期。
- 默认 `reported` 只比较同来源、同作物口径、同地区、相邻目标年，优先同一原始报告；可得日期不能晚于当前记录。它允许上年原记录为 Forecast，但明确展示该标签。
- `estimate` 严格要求同源上年 Estimate；`actual` 严格要求同口径官方 Actual。缺失时不偷偷换基准。
- `reason=no_compatible_prior_year` 表示基准缺失；`zero_prior_year` 表示上年产量为0、同比无法定义；`no_observation_for_selection` 表示当前筛选无产量记录。N/A 不代表产量或同比为零。
- 本次新增的季节稻谷口径 `paddy_semi_late` 与全年 `paddy`、早稻 `paddy_early` 分组，冬小麦仍为 `winter_wheat`。

## 可审计接口

`/api/outlook/rice?target_year=2026&subregion=Southeast%20Asia&baseline=reported`

Python API返回所选年度/区域的逐国生产、同比基准、缺失原因和覆盖计数。`/api/production?crop=rice&country=Myanmar` 同样能查到源库中的 Burma。

静态文件 `public/api/asia_coverage.json` 对五作物、19个国家/地区逐格公布数量、同比、单位口径、来源与可得日期；随 `build_web_data.py` 自动更新。国家在原始源中未覆盖、该作物产量为0或无官方预测时，继续保留真实缺口。

## 已复现的同比

| 2026/27 作物与国家 | 来源 | 当前量 Mt | 上年报告量 Mt | 同比 |
|---|---|---:|---:|---:|
| 精米 / 缅甸 | USDA WASDE | 11.00 | 12.00 Estimate | -8.33% |
| 精米 / 韩国 | USDA PSD | 3.49 | 3.539 Forecast | -1.38% |
| 精米 / 马来西亚 | USDA PSD | 1.65 | 1.60 Forecast | +3.13% |
| 糖 / 泰国 | USDA PSD | 9.50 | 11.258 Forecast | -15.62% |
| 玉米 / 印度尼西亚 | USDA PSD | 13.50 | 13.30 Forecast | +1.50% |

以上为最新现存快照的产量同比，不是月度预测修正，也不代表直接厄尔尼诺因果影响。

## CropWatch 新格式处理

本次联网执行 `python scripts/fetch_cropwatch.py --reports 4` 成功。CropWatch总计656条生产/面积/单产记录，其中Forecast554、Estimate102；2026年中国国家与省级数据覆盖4月、6月、8月，旧版本继续保留。最新全国值（Mt）为：玉米266.18、稻谷210.05、小麦140.96、大豆19.67；这些是CropWatch来源口径，不代替其他机构或最终官方实产。

原始HTML、图片和内容哈希永久归档。可读表格按每列明确年度/单位解析；仅有百分比时不倒推未发布的上年产量。2026年6月和8月的附录图片按SHA256绑定经逐格核验的亚洲转录，源图片变化即拒绝套用旧转录，并在来源状态中提示需要重新核验。已获取新报告时自动发现中国章节、国家附录和表格图片。

2026年4月附录中印尼、泰国、越南部分稻米数量对应旱季，表格未完整注明季节，排除全年比较；6月中国部分夏粮/小麦表题与数量存在矛盾，隔离后采用独立附录。8月附录与正文的Global Rice/Wheat合计也有差异，因此图片转录只采用已审查的亚洲国家行，不用图片Global行覆盖原Global记录。

源文件中的同比百分比保存在 `data/vintage/cropwatch/*.json` 的 `source_yoy`，平台计算的同比基于所列明确数量，两者可能因原文取整或内部不一致而不同。不得把一张图的不同口径硬凑为一致数值。

## 验证与当前覆盖

- 2026年五作物×19个国家/地区共95格：有当前预测74格、可计算同比52格。逐格原因见静态覆盖台账；零产量不当作同比0%。
- 中国玉米as-of 2026-07-31返回CropWatch268.75 Mt；当前返回8月版266.18 Mt；两个版本同时保留。
- 水稻下选择CropWatch，泰国为39.18 Mt、稻谷口径；选择USDA则为20.30 Mt、精米口径。两者不合并计算共识或跨口径比较。
- `pytest` 43 passed；数据完整性与源文件SHA256全部通过；前端数据契约和生产构建通过。
- 生产静态站Playwright验证：东亚/东南亚聚焦、缅甸/韩国映射、泰国糖同比、Actual严格无降级、中国四作物、2026河南下钻、历史as-of、源切换通过；桌面/手机无运行错误或横向溢出。
- 本地3000开发页面已恢复；3001静态预览与8010 API继续可用。本次未另建定时任务，已有每日更新入口自动使用新版解析器。
