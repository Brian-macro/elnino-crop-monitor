# Brian的厄尔尼诺看盘

[在线网站](https://brian-macro.github.io/elnino-crop-monitor/) · [GitHub仓库](https://github.com/Brian-macro/elnino-crop-monitor) · [定时更新与部署记录](https://github.com/Brian-macro/elnino-crop-monitor/actions)

已部署至GitHub Pages。数据库以Parquet表快照保存在仓库，Actions每天北京时间14:17检查到期来源、更新数据并重新部署；无需本机持续开机或运行数据库服务器。

Global Crop Production, Climate Risk & Commodity Pricing

最新研究审计见 [docs/RESEARCH_AUDIT_2026-09-08.md](docs/RESEARCH_AUDIT_2026-09-08.md)：网站定位为描述性复盘。已统一NOAA官方ONI ERSSTv6公布表、增加行情月度样本筛选、明确市场年度与自然月及PSD/WASDE全球消费差异，不能将叠图直接当作套利或因果回测。

面向投资研究的可运行网站。保留已有 Next.js + ECharts + Python + DuckDB 架构，接通真实数据、预测版本、世界地图、国家/省级下钻、五作物价格研究、气候周期、历史事件与来源台账。

中文浅色Dashboard：地图首屏、下方品种切换、前五国家/地区+其他；统一PSD可比口径。首页“查看历史、价格与预测修正”入口已移除。历史复盘页独立展示内外盘、ONI与USDA年度供需。验收脚本：`node tests/dashboard_browser.cjs`、`node tests/event_study_browser.cjs`。

本次是从半成品继续构建，接手目录没有 Git 仓库。接手基线、修复范围和验收记录见 [docs/CONTINUATION.md](docs/CONTINUATION.md)。不把尚未获得的数据当成已实现覆盖。

后端现按研究地区组织：东南亚是固定成员的地区汇总，海外主序列统一PSD；非生产者和小规模作物按配置剔除。中国NBS/CropWatch/农业展望分工明确，Actual/Forecast及不同口径保持独立。完整方案见 [docs/DATA_STITCHING.md](docs/DATA_STITCHING.md)，唯一研究配置为 [config/research_policy.json](config/research_policy.json)。

## 启动

```powershell
pip install -r requirements.txt
npm ci
npm run dev -- --hostname 127.0.0.1 --port 3000
```

打开 http://127.0.0.1:3000 。仓库已提供真实数据生成的 `public/api/*.json`，预览不需先联网抓取。生产构建 `npm run build`，之后 `npm start -- --port 3001` 提供 `out/` 静态站。

## 已连接的数据与页面

- 五作物：Wheat / Corn / Soybean / Rice / Sugar；Global及主要生产国。
- Actual、Forecast、Estimate独立表；不可变原始归档；逐报告预测vintage；按as-of筛选。
- 世界地图、同比基准选择、机构选择、中国2025省级下钻；无数据N/A。
- USDA PSD历史估计、WASDE两个月预测；CropWatch国家/省级；农业展望公开摘要；NBS实产。
- Niño3.4、ONI当前异常、历史分位、历史周期和事件窗口。
- 历史复盘：国内玉米/豆一/豆二/白糖/粳米/强麦主连，外盘玉米/大豆/小麦/原糖；期货与现货参考明确分开，缺年缺月显示“数据缺失”。
- 供需库存、描述性天气风险定价变量；缺失天气/作物历/进口平价明确N/A。
- 完整来源状态、原始文件哈希、日期证据；已使用用户提供的公众号二维码和圆形头像，Brian介绍保留用户原文。

## 数据更新与恢复

期货：`python scripts/fetch_futures.py`，合约映射在 `config/futures_contracts.json`。使用与AkShare相同的新浪接口直接归档原始JSONP，无需在运行时安装AkShare。期货存于独立`futures_prices`表，日更已加入统一调度；`MONITOR_OFFLINE=1`可从本地原始数据重放。强麦源停在2023年、外盘稻米暂未连接，页面如实显示数据缺失。

```powershell
python scripts/update_all.py --group scheduled
python scripts/validate.py
python scripts/export_database.py
```

默认`scheduled`按配置只检查到期来源，`--dry-run`预览任务；`all`强制全源，`climate`/`crops`/`reference`/`prices`指定来源组，`build`仅重新生成。日志在 `data/logs/`；源失败保留旧数据并继续其他源，完整性或发布失败阻止部署。开发站刷新即可看到更新，静态部署须重建。

需要从便携数据恢复时：`python scripts/build_database.py --db data/processed/restored.duckdb`。命令拒绝覆盖已有库。将 `MONITOR_DB` 指向新库以切换。默认库为 `data/processed/monitor_v2.duckdb`；早期 `monitor.duckdb` 保留。

## 自动运行与部署

Windows：`powershell -ExecutionPolicy Bypass -File scripts/register_update_task.ps1 -Time 14:17`。

GitHub：`update-data.yml` 每日更新、持久化原始文件和vintage，直接部署新数据提交；`deploy.yml` 支持Pages根站和项目子路径。当前尚无Git远程仓库，云端工作流需要上传到用户自己的仓库后启用。

容器、Windows调度、API和完整部署步骤见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。环境变量模板见 `.env.example`，前端变量放 `.env.local`，Python变量设置在执行环境。

## 可选只读 API

```powershell
python -m uvicorn api:app --app-dir scripts --host 127.0.0.1 --port 8010
```

OpenAPI在 http://127.0.0.1:8010/docs 。静态站可直接读取 `/api/wheat.json`、`/api/elnino.json` 等；动态API支持来源、国家、地区、目标年、数据类型、口径和历史可得日期过滤，并可下载原始证据。

## 如何扩展

新机构：在 `scripts/config.py` 的 `SOURCES` / `STALE_DAYS` 注册，新增 `fetch_<source>.py`，调用 `archive.download`、`observation`、`db.insert_rows` 和 `save_parsed`，失败用 `failed`；将真实原文样例加入解析测试，再加入 `update_all.py`。官方实产必须有明确证据，不能仅因目标年已过就改为Actual。

新作物：同步 `config.py` 的 `CROPS` / `BASIS`、来源解析映射、`lib/data.ts` 的 `CROPS` / `names`、`app/[crop]/page.tsx` 的静态路由、导航和价格映射。重新构建JSON和网站。

新国家/地区：修改 `config/research_policy.json` 的 `active_countries`、`regions.members_by_crop`并升级政策版本；不要编辑自动派生的`COUNTRIES`。补齐源名称/地图名称和筛选证据，执行`python scripts/write_policy_docs.py`与`--group build`。原始国家全集仍保留，但研究层只纳入有意义的作物生产者。

更新频率：统一修改 `research_policy.json.schedule.interval_days`；GitHub和Windows每天唤醒，实际按来源配置检查。陈旧度阈值在 `STALE_DAYS`，Last Checked与最新观测期分开记录。

公众号：默认使用用户原图`public/images/brian-wechat.jpg`；头像原图`brian-avatar.jpg`保留，页面使用等比缩小的WebP。可以用`NEXT_PUBLIC_WECHAT_IMAGE`覆盖二维码路径。没有生成替代二维码。Brian页面已使用用户提供的介绍。

## 验证

```powershell
python -m pytest -q
python scripts/validate.py
node tests/data_contract.cjs
npm run typecheck
npm run build
```

浏览器测试：环境安装Playwright且有Chrome时运行 `node tests/dashboard_browser.cjs`；默认访问本地3000端口，可通过 `TEST_URL` 修改。输出桌面/平板/手机截图及错误记录至 `test-results/`。旧版的browser_smoke/asia_browser/regional_browser保留作此前界面审计记录，不作为新版首页的验收入口。

## 研究边界

PSD历史是修订后Estimate；NBS当前仅2025三谷物Actual。CropWatch已恢复656条，完整旧报告仍未覆盖；农业展望仅6条明确预测，不能插值出2027。海外为World Bank月度现货基准，国内为少量NBS旬度报价，非交易所期货。缺少同口径独立机构和足够国内价格历史时，共识/相关性N/A。事件结果为描述性关联，不能视为气候因果估计。

完整覆盖、定义、单位和未接通数据见 [docs/DATA_SOURCES.md](docs/DATA_SOURCES.md)；数据库schema见 [docs/schema.sql](docs/schema.sql)。
