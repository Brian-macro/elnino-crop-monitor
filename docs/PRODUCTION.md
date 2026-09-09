# 生产部署

网站：https://brian-macro.github.io/elnino-crop-monitor/

公开仓库：https://github.com/Brian-macro/elnino-crop-monitor

首次部署：[Deploy to GitHub Pages](https://github.com/Brian-macro/elnino-crop-monitor/actions/runs/34243621193)，成功。

云端更新闭环：[Update Research Data](https://github.com/Brian-macro/elnino-crop-monitor/actions/runs/34245791900)，成功。该次运行完成数据库恢复、NOAA更新、数据校验、快照提交以及Pages再部署。

曾有一次更新后的Pages产物上传与并行部署同名，返回403。工作流现为每次运行生成唯一产物名；修复后的直接部署和完整数据更新均已验证成功。

## 运行方式

数据库文件存放在GitHub仓库，Actions是执行器，不是持久数据库。持久化内容包含schema、Parquet表快照、不可变原始资料及预测版本。每次运行恢复为临时DuckDB，完成校验和更新后重新导出、提交，并发布静态网站。

`.github/workflows/update-data.yml`每天06:17 UTC（北京时间14:17）启动。默认运行 `python scripts/update_forecasts.py`，每日检查预测来源。同日已检查则跳过。手动运行可以选择 forecasts、scheduled、climate、crops、reference、prices、all 或 build；scheduled/all 是显式维护操作，不用于每日自动任务。

前端由GitHub Pages提供，访问不依赖本机3000或8010端口。生产数据接口为站点下`api/*.json`；本地FastAPI仅作查询开发用途。

未向仓库上传登录凭据、环境密钥、本地日志、node_modules或运行中的DuckDB文件。原始文件禁用Git换行转换，已核验Git索引中的65份来源文件SHA256与台账一致。

## 两部分数据与每日流程（2026-09-09）

1. 基础数据：PSD 历史及回退基线、NBS 实产、气候、现货、期货。保存在仓库 Parquet，不每日重新抓取。
2. 预测数据：WASDE、CropWatch、CASDE、本土机构与中国农业展望。原始报告与解析版本追加保存，预测报告中的上年可比值也保留，用于同源成对同比。

每日北京时间14:17：checkout main → 恢复DuckDB → update_forecasts.py → 校验 → 生成本土拼接JSON → 导出Parquet → 提交数据 → 部署确切提交。预测组不调用 fetch_usda.py、fetch_noaa.py、fetch_nbs.py、fetch_prices.py 或 fetch_futures.py。基础库保持已有时间覆盖，新增季节需要手动维护PSD基线。

Pages 的普通 `push` 只处理代码、配置和静态资产。数据提交只由 `Update Research Data` 在校验、JSON 发布和 Parquet 导出成功后通过 `workflow_call` 部署，避免同一快照被自动部署两次。

GitHub Actions runner 是临时执行环境，数据库的长期保存位置是 GitHub 仓库，而非 runner 磁盘或有期限的 artifact/cache。日志 artifact 仅保留30天，不承担数据库备份职责。

手动维护：Actions 的 Run workflow 选择对应 group；仅重建页面选 build，全量刷新选 all。单源失败保留旧版并发布来源状态，数据完整性检查失败则禁止提交和部署。

已知限制：部分本土适配器（例如 AAFC、CONAB、DA&FW）仍绑定已验证的具体报告URL；每日会检查该报告的内容修订，但尚不能保证自动发现下一期新URL。固定端点的报告发布日期不得随检查日期刷新；新报告需补充发现和口径验证后接入。每日检查成功不等于发现新预测。

## 本次云端验收

代码提交 `fe1bf99` 已推送 main；数据保存提交 `1d07145`。预测更新运行：https://github.com/Brian-macro/elnino-crop-monitor/actions/runs/34300403854 。

云端92项测试通过；WASDE、CropWatch、中国农业展望返回0；CASDE与本土机构当日已检查而跳过。校验、JSON发布与Parquet导出全部成功，report.group=forecasts、publication_complete=true、ok=true。基线生产、气候与价格Parquet未改变。本地另通过快照重建、TypeScript、14页静态构建、桌面与移动端两套浏览器回归。
