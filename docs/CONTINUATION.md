# 接续审计与验收 · 2026-09-08

> 最新后端已按地区重构，单一政策配置与历史/预测拼接见 [DATA_STITCHING.md](DATA_STITCHING.md)。

> 后续亚洲数据修复已经完成，新增2026年中国与亚洲多版预测、区域覆盖和同比后端；最新结果见 [ASIA_DATA.md](ASIA_DATA.md)。下方保留首次接续的审计基线。

## 接手基线

此目录及父目录均没有 `.git`，`git status` / `git diff` / `git log` 返回 not a git repository。没有可用的提交或差异历史，不能把所有文件当成本次新增。

最近修改：16:41 地图 Outlook / Revision；16:38 JSON、lib/data.ts 与新 DuckDB；16:35 报告抓取脚本。旧 app 页面、CSS、工作流、README 停留在 14:18–14:38，未接入新数据契约。

已完成并保留：Next.js/React/ECharts；monitor_v2.duckdb 独立 Actual/Forecast/Estimate 表；内容哈希原始文件归档；PSD 1960–2026 数据；NOAA ONI、Niño3.4；WASDE 2026-07/08；World Bank 五作物价格；NBS 部分实产及国内现货；CropWatch 4 条预测；农业展望 6 条预测；JSON 构建器；世界 GeoJSON；地图/修正组件。旧 monitor.duckdb 与原始归档保留。

基线验证：pytest 9 passed；validate.py 查询不存在的旧 production 表而失败；tsc 因旧页面契约与缺失 target 配置失败；out/ 是过期构建。

## 本次接续计划

用户已授权在当前状态直接完成，沿用 docs/IMPLEMENTATION.md 中的架构和设计，不重新设计或另建项目。

- [x] 修复 v2 数据校验，补充来源、单位、版本、时间点和计算回归测试。
- [x] 接入已有 Outlook / Revision，完成 Overview、五作物历史/价格/库存、气候、事件、方法和 About 页面。
- [x] 价格 Raw 按币种分轴；Indexed 使用共同实际月份，Z-score 分序列计算；相关性只使用对齐的连续月收益，不足样本返回 N/A。
- [x] 事件使用 NOAA ≥5 个连续暖季筛选和 T±12 月窗；产量 Estimate / Actual 明示，趋势仅用之前 10 年；不输出因果结论或精确 price-in 百分比。
- [x] 增加只读 Python API、更新总入口、失败状态持久化、数据库重建与 Parquet 导出；补齐依赖、环境变量、部署和调度。
- [x] 检查真实归档和数据量、运行 ETL、构建、API 与浏览器交互；记录覆盖缺口与可复现命令。

## 验收边界

不得将 PSD 历史估计提升为官方 Actual；下载日未知发布日期必须明示；中国 Forecast 仅 CropWatch / 农业展望。没有可靠 2027 数据、省级数据、国内糖价格、期货或天气格点时显示 N/A。年度/精米稻谷定义不同不计算共识。完整历史报告的公开获取与格式解析仍受官方可用性限制，逐源披露。

## 最终验收

- `python -m pytest -q`：27 passed。涵盖原始内容修订不回填、日期补证审计、重放保留联网状态、NBS/CropWatch真实原文解析、独立水稻单产、NOAA观测期末、PSD多快照全球合计、API as-of、缺失月份/相关性和更新失败隔离。
- `python scripts/validate.py`：0 hard failures，全部原始文件SHA256、证据关联、日期、口径、单位和唯一性通过。
- `node tests/data_contract.cjs`：通过；默认全年稻谷而非早稻，显式季节选择保留；预测修正遵守月份基准。
- `npm run typecheck` / `npm run build`：通过，生成14个静态页面，无编译警告。
- Playwright真实Chrome：1440×1080、390×844；五作物、2025中国→河南下钻、2027 N/A、三种价格模式、作物页跨品种导航、ONI切换、历史事件与作物、来源/About/地图路由，以及加载失败重试状态通过。地图/气候/事件画布非空；无页面错误、失败HTTP请求或移动端横向溢出。
- Parquet恢复到临时新DuckDB通过完整性验证；验证用库随后删除。
- 本地API `/health` 返回38份源文件；as-of 2026-07-31 的Global Wheat/2026生产预测为 USDA WASDE 819.97 Mt，available 2026-07-10。

## 真实数据快照

Actual 9条指标；Estimate 254,648条；Forecast 9,258条；38份source documents；25个省级region标签；4,000条海外价格、36条国内价格；22段经典ONI暖事件。Forecast原始版本：WASDE 2、CropWatch 2、PSD 1、农业展望1。CropWatch本次从4条恢复为168条；NBS从6条恢复为9条。

这些数据量不代表覆盖完整。全量联网更新（2026-09-08 10:00 UTC）中 NOAA、PSD 成功；WASDE、CropWatch、农业展望、World Bank、NBS 遇到连接重置/502。旧数据保留，失败状态已发布到网站，整个run标记不完整；校验/JSON/Parquet步骤通过。单独气候更新全部成功。详情在 `data/logs` 和 `data/last_update.json`。

## 运行状态

- 开发站：http://127.0.0.1:3000
- 生产静态预览：http://127.0.0.1:3001
- 只读API/OpenAPI：http://127.0.0.1:8010/docs
- Windows任务 `ElNinoCropMonitor-Update` 已注册Ready；每日本机14:17，下一次2026-09-09 14:17。未等待未来定时执行；本次手动执行已验证运行链路。
- 云端Pages/容器配置已交付，但因当前目录无Git远程且未发布，不声称云端部署已生效。

仍未完整实现的原始需求见 `docs/DATA_SOURCES.md`：完整历史预测矩阵、2027、其他官方机构、国内长期期货/价格、地区天气、作物历、进口平价与同口径多机构覆盖。缺失数字继续显示N/A。
