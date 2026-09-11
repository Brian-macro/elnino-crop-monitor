# 项目事实与运行入口

- 产品：Brian的厄尔尼诺看盘。
- 仓库：https://github.com/Brian-macro/elnino-crop-monitor
- 可见性：用户于 2026-09-11 确认当前 GitHub 套餐不支持私有仓库 Pages 后，授权仓库恢复公开，网站继续通过公开 GitHub Pages 发布。
- 生产站：https://brian-macro.github.io/elnino-crop-monitor/
- 已验证云端更新闭环：https://github.com/Brian-macro/elnino-crop-monitor/actions/runs/34245791900
- 默认分支：main。GitHub Pages使用GitHub Actions部署。
- 数据持久化：`data/processed/parquet/*.parquet`为完整数据库表快照，schema在`scripts/db.py`及`docs/schema.sql`。`data/raw`与`data/vintage`永久保留。
- GitHub Runner通过`build_database.py`恢复DuckDB；DuckDB工作文件不提交，不需要长期运行数据库服务。页面读取`public/api/*.json`静态数据接口。
- 自动更新：`.github/workflows/update-data.yml`每天06:17 UTC（北京时间14:17）唤醒；每日只运行`python scripts/update_forecasts.py`检查预测来源；基础库手动维护。`config/research_policy.json`中`data_part`区分baseline和forecasts，同日已检查的预测来源跳过。
- 更新必须通过数据校验、JSON发布、Parquet导出，然后提交快照并直接调用`deploy.yml`部署确切提交。单源失败保留旧数据与Stale状态，完整性失败不得发布。
- Pages产物名包含GitHub run id与attempt，避免并行部署的artifact重名冲突。
- `.gitattributes`对原始资料与历史解析快照禁用换行转换；不得格式化、覆盖或修改原始文件，否则会破坏证据哈希。
- 研究定义与已知限制见`docs/RESEARCH_AUDIT_2026-09-08.md`；研究范围与来源策略以`config/research_policy.json`为准，期货合约映射见`config/futures_contracts.json`。
- 验证：`python -m pytest -q`、`python scripts/validate.py`、`npm run typecheck`、`npm run build`。浏览器验证用`tests/dashboard_browser.cjs`和`tests/event_study_browser.cjs`。

- 本土来源一致性：`dashboard_bundle` 为首页默认预测产量计算入口；历史复盘默认只读取 `actual_production`。PSD/WASDE 完整供需表独立展示，禁止混源生成库存消费比。
- `country_sources.json` 决定各国各作物本土来源；有本国预测数据用本国预测数据，无则用PSD。`policy_bundle` 导出的来源矩阵是配置，不是实际采用覆盖承诺。
- 气候是独立NOAA归档观测；连续暖季不能跨缺月，1/3月变化按日历月。本机旧 `ElNinoCropMonitor-Update` 定时任务已停用，日更由GitHub Actions执行。
- 文档生成器 `write_policy_docs.py` 只生成 `docs/SOURCE_MATRIX.md`，不覆盖人工审定的 `DATA_STITCHING.md`。
- 换源回归：`tests/test_source_consistency.py`、`tests/test_climate_continuity.py`、`tests/source_consistency_browser.cjs`、`tests/climate_browser.cjs`。
- 乌克兰 UGA 使用收获自然年，对应同年开始的市场年度；2026/2025 同源配对用于 2026 年预测同比。阿根廷 BCR 使用市场年度起始年。
- `fetch_local_sources.py` 单源失败已自行登记状态时返回 2，避免调度器把其他成功来源统一标记失败；解析 PDF 所需 `pypdf` 必须安装到云端。
