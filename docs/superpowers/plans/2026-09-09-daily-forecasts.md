# 每日预测更新实施计划

目标：沿用已批准的本土优先、同源成对同比设计，将每日联网更新限定为预测来源。

架构：GitHub 仓库保存基础库与预测版本两部分，使用现有 Parquet 表与不可变 raw/vintage；Actions 恢复临时 DuckDB，调用独立预测脚本，校验并发布后提交快照，再部署该提交。

- [x] 核查当前代码、未提交修正、政策与工作流。
- [x] 增加调度回归测试：基础来源不进入每日任务、同日跳过、次日检查、手动全量仍可用；运行并确认失败。
- [x] 在 schedule 标明 data_part；forecasts 组每日检查预测来源，保留旧手动维护组。
- [x] 新增 scripts/update_forecasts.py，复用既有锁、失败隔离、校验与导出。
- [x] 工作流默认 forecasts，恢复 main 最新快照，保存确切提交后部署。
- [x] 全量 pytest（92 passed）、validate、快照恢复、typecheck、build。
- [ ] 更新运行文档、提交推送、验证云端运行。

基础部分：PSD 历史与回退基线、NBS 实产、气候、现货及期货；只手动更新。
预测部分：WASDE、CropWatch、CASDE、本土机构、中国农业展望；保留报告中的可比上年实产/估计，这些是预测拼接所需证据，不等于重抓历史库。
不采用 Actions artifact/cache 作为唯一持久数据库，因为 runner 为临时实例且 artifact/cache 有生命周期。
