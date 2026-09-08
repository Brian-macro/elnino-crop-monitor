# 生产部署

网站：https://brian-macro.github.io/elnino-crop-monitor/

公开仓库：https://github.com/Brian-macro/elnino-crop-monitor

首次部署：[Deploy to GitHub Pages](https://github.com/Brian-macro/elnino-crop-monitor/actions/runs/34243621193)，成功。

云端更新闭环：[Update Research Data](https://github.com/Brian-macro/elnino-crop-monitor/actions/runs/34245791900)，成功。该次运行完成数据库恢复、NOAA更新、数据校验、快照提交以及Pages再部署。

曾有一次更新后的Pages产物上传与并行部署同名，返回403。工作流现为每次运行生成唯一产物名；修复后的直接部署和完整数据更新均已验证成功。

## 运行方式

数据库文件存放在GitHub仓库，Actions是执行器，不是持久数据库。持久化内容包含schema、Parquet表快照、不可变原始资料及预测版本。每次运行恢复为临时DuckDB，完成校验和更新后重新导出、提交，并发布静态网站。

`.github/workflows/update-data.yml`每天06:17 UTC（北京时间14:17）启动。`scheduled`按配置挑选到期来源；手动运行时可以选择climate、crops、reference、prices、all或build。

前端由GitHub Pages提供，访问不依赖本机3000或8010端口。生产数据接口为站点下`api/*.json`；本地FastAPI仅作查询开发用途。

未向仓库上传登录凭据、环境密钥、本地日志、node_modules或运行中的DuckDB文件。原始文件禁用Git换行转换，已核验Git索引中的65份来源文件SHA256与台账一致。
