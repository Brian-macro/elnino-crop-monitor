# 项目事实与运行入口

- 产品：Brian的厄尔尼诺看盘。
- 仓库：https://github.com/Brian-macro/elnino-crop-monitor
- 生产站：https://brian-macro.github.io/elnino-crop-monitor/
- 已验证云端更新闭环：https://github.com/Brian-macro/elnino-crop-monitor/actions/runs/34245791900
- 默认分支：main。GitHub Pages使用GitHub Actions部署。
- 数据持久化：`data/processed/parquet/*.parquet`为完整数据库表快照，schema在`scripts/db.py`及`docs/schema.sql`。`data/raw`与`data/vintage`永久保留。
- GitHub Runner通过`build_database.py`恢复DuckDB；DuckDB工作文件不提交，不需要长期运行数据库服务。页面读取`public/api/*.json`静态数据接口。
- 自动更新：`.github/workflows/update-data.yml`每天06:17 UTC（北京时间14:17）唤醒；`config/research_policy.json`决定哪些来源到期。统一入口为`python scripts/update_all.py --group scheduled`。
- 更新必须通过数据校验、JSON发布、Parquet导出，然后提交快照并直接调用`deploy.yml`部署确切提交。单源失败保留旧数据与Stale状态，完整性失败不得发布。
- Pages产物名包含GitHub run id与attempt，避免并行部署的artifact重名冲突。
- `.gitattributes`对原始资料与历史解析快照禁用换行转换；不得格式化、覆盖或修改原始文件，否则会破坏证据哈希。
- 研究定义与已知限制见`docs/RESEARCH_AUDIT_2026-09-08.md`；研究范围与来源策略以`config/research_policy.json`为准，期货合约映射见`config/futures_contracts.json`。
- 验证：`python -m pytest -q`、`python scripts/validate.py`、`npm run typecheck`、`npm run build`。浏览器验证用`tests/dashboard_browser.cjs`和`tests/event_study_browser.cjs`。
