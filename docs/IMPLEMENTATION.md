# 续建方案与扫描结果 · 2026-09-08

> 本文件保留前一轮的扫描基线；下方未勾选清单不代表当前完成状态。本次接续结果、数据覆盖和验证请看 [CONTINUATION.md](CONTINUATION.md)。

用户已给定完整产品需求并要求在现有目录直接完善。保留 Next.js / ECharts / Python / DuckDB；不重建另一套项目。

## 扫描结果
- 已有五个作物页、ONI 页和 2026-08-12 PSD 单一快照。
- 旧 production 表混用 actual/forecast；固定年份分类无法支持历史 vintage。
- 全球是 21 个国家/地区的部分合计，缺失官方全球口径。
- CropWatch、农业展望和价格 downloader 是返回成功的占位脚本。
- 图表缺少 source date、as-of 和可靠 stale 状态。
- 静态导出 assetPrefix='./' 会导致深层页面资源路径错误；更新 workflow 的 bot commit 不保证触发部署。
- 工作目录没有 Git 仓库；不删除已有原始文件和旧 DuckDB。

## 实施顺序
- [ ] 数据层：独立 actual / forecast / estimate 表，统一证据表、不可变 archive、时间点查询；新库 monitor_v2.duckdb 保留旧库。
- [ ] 真实源：PSD 全部国家历史（未明确终值只标 estimate）、NOAA ONI + Niño3.4、WASDE archive、World Bank 价格、CropWatch / 农业展望官方报告发现和解析。
- [ ] 质量层：单位与口径校验、错误保留旧数据、报告哈希、真实发布日期与下载日期分开，未知时间不冒充 publication date。
- [ ] API 与 JSON：按作物/来源/年度/状态/as-of 查询；价格三种模式、同比、滞后趋势、修正和事件窗口。
- [ ] 前端：高密度深色研究终端，石墨底、琥珀选中态、细分隔线、等宽数字、小圆角；世界地图为主视觉，五作物/气候/事件/方法/About 全导航。
- [ ] 自动化：单一更新入口、分源频率、完整归档持久化、更新后直接部署；本地 Windows 任务配置与容器部署。
- [ ] 验证：数据回归测试、真实 ETL、API 测试、Next 构建、浏览器交互与移动布局；记录未接通数据的具体原因。

## 研究边界
PSD 的历史最新估计不是官方最终 Actual，也不是当年的历史预测。中国 Forecast 默认仅 CropWatch / 中国农业展望。Paddy / milled、calendar / marketing year 严格分组。不同定义或仅一来源不制造 consensus/dispersion。2027 没有真实 forecast 就显示 N/A。事件结果是描述性关联，不作为气候因果估计。微信图片为空时显示明确占位。
