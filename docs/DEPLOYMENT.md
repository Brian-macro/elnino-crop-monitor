# 部署与定时更新

## 本地预览

```powershell
pip install -r requirements.txt
npm ci
npm run dev -- --hostname 127.0.0.1 --port 3000
```

网站在 http://127.0.0.1:3000 。若端口被占用，替换 `--port`。生产静态版本：`npm run build` 后执行 `npm start -- --port 3001`。

## 数据更新

```powershell
python scripts/update_all.py --group scheduled
python scripts/update_all.py --group scheduled --dry-run
python scripts/update_all.py --group all
python scripts/update_all.py --group climate
python scripts/update_all.py --group crops
python scripts/update_all.py --group prices
python scripts/update_all.py --group build
```

源失败返回 2，保留其上次数据，并继续更新其他来源；完整性失败禁止发布新 JSON。各步日志在 `data/logs/<UTC run>/`，总结果在 `data/last_update.json`。`data/.update.lock` 防止并发写库；只有确认旧进程已停止时才可删除遗留锁。

前端开发服务器读取 `public/api/*.json`，刷新即可看到更新；静态 `out/` 或容器在数据更新后需要重新构建。静态 JSON API 无需额外数据库服务。

## Windows 每日任务

```powershell
powershell -ExecutionPolicy Bypass -File scripts/register_update_task.ps1 -Python python -Time 14:17
Get-ScheduledTask -TaskName ElNinoCropMonitor-Update
```

此配置每日在本机时间14:17运行`scheduled`组，由`config/research_policy.json`选择到期来源。更改`interval_days`修改各源频率，`-Time`仅改变每天唤醒时间。默认以当前用户运行，本机需要开机并具备联网环境。禁用：`Disable-ScheduledTask -TaskName ElNinoCropMonitor-Update`。

本次接续已在当前机器注册该任务，状态Ready，首次计划运行时间为2026-09-09 14:17；无需重复注册。

## GitHub Pages

项目接手时没有 `.git` 或远程仓库，尚未发布到互联网。将项目纳入自己的 GitHub 仓库后，Settings → Pages → Source 选择 GitHub Actions。提交源代码、`data/raw`、`data/vintage`、`data/processed/parquet`、`data/web`、`public/api`。DuckDB 工作库、依赖和构建缓存不纳入 Git。

`.github/workflows/update-data.yml`每日06:17 UTC启动，`scheduled`仅检查配置中到期的来源，也支持手动强制指定组。它从Parquet恢复数据库后运行统一入口，要求`publication_complete=true`才提交与部署。源站单项失败可发布旧有效数据和Stale状态；校验/JSON/Parquet任何一步失败禁止部署。新提交SHA显式传入部署，无需依赖bot push。修改`research_policy.json.schedule`即可改变分源更新频率。

`deploy.yml`在每次构建时从提交的Parquet恢复并用当前policy重建JSON，因此只改研究配置也不会部署旧成员名单。云端无生产DuckDB依赖；整个流程可以在Linux或本地从便携数据复现。

`deploy.yml` 对项目站自动设置 `/repository-name`，对 `name.github.io` 根站使用空路径。自定义根域部署时将该环境变量设为空。客户端资源、地图和 API 路径共同使用 `NEXT_PUBLIC_BASE_PATH`，不要使用 `assetPrefix: './'`。

## 容器静态站

```bash
docker build -t elnino-crop-monitor .
docker run --rm -p 8080:80 elnino-crop-monitor
```

容器发布构建时的数据快照；更新数据并重新构建镜像即可更新。Dockerfile 用 Nginx 提供 Next 静态文件和目录路由。

## 可选 Python 查询 API

```powershell
python -m uvicorn api:app --app-dir scripts --host 127.0.0.1 --port 8010
```

OpenAPI 文档：http://127.0.0.1:8010/docs 。支持 `/api/production?crop=wheat&country=Global&target_year=2026&status=forecast&asof=2026-07-31`、`/api/crops/wheat?asof=2026-07-31`、`/api/climate`、`/api/sources` 和原始证据下载 `/api/documents/{document_id}/raw`。生产查询默认遵守中国预测来源策略。写库更新时短暂锁冲突返回 503，可重试；公开站优先使用静态 JSON API。

## 数据库恢复

```powershell
python scripts/export_database.py
python scripts/build_database.py --db data/processed/restored.duckdb
```

恢复器拒绝覆盖已有数据库，并校验原始文件哈希与证据关联。使用新路径设置 `MONITOR_DB` 才会切换工作库。`docs/schema.sql` 与 `scripts/db.py` 是同一 v2 schema；旧 `monitor.duckdb` 继续保留，不能混用旧 `production` 表。

`MONITOR_OFFLINE=1` 只读取已有归档，不视为成功联网检查。`replay_archive.py` 重新解析 CropWatch/农业展望归档并记录日期补证，不覆盖旧解析快照和旧源站失败状态。
