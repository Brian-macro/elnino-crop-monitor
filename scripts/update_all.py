"""Single writer; source failures retain data and do not stop other fetchers."""

import argparse, json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path
from config import ROOT, DATA
from policy import POLICY
from scheduler import select_jobs


def run_steps(steps, log_dir):
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    result = []
    for name, args in steps:
        start = time.monotonic()
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        try:
            p = subprocess.run(
                [sys.executable, *args],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=900,
            )
            code = p.returncode
            output = p.stdout + p.stderr
        except subprocess.TimeoutExpired as e:
            code = 124
            output = "Source update timeout: " + str(e)
        if code in (1, 124):
            from config import SOURCES
            from db import connect, mark_source

            affected = [
                key
                for key, cfg in SOURCES.items()
                if cfg["script"] == Path(args[0]).name
            ]
            if affected:
                with connect() as con:
                    for source in affected:
                        mark_source(
                            con,
                            source,
                            False,
                            error="Updater failed: " + output[-1200:],
                        )
        (log_dir / (name + ".log")).write_text(output, encoding="utf-8")
        print(name, "exit", code, flush=True)
        result.append(
            dict(step=name, returncode=code, seconds=round(time.monotonic() - start, 2))
        )
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--group",
        choices=[
            "scheduled",
            "forecasts",
            "all",
            "climate",
            "crops",
            "reference",
            "prices",
            "build",
        ],
        default="scheduled",
    )
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)
    if args.offline:
        os.environ["MONITOR_OFFLINE"] = "1"
    from db import connect

    with connect() as con:
        last_checked = {
            source: stamp
            for source, stamp in con.execute(
                "SELECT source,last_checked FROM source_metadata"
            ).fetchall()
        }
    jobs = select_jobs(
        POLICY["schedule"],
        last_checked,
        group=args.group,
        due=args.group in ("scheduled", "forecasts"),
    )
    steps = [(job["id"], ["scripts/" + job["script"], *job["args"]]) for job in jobs]
    if args.dry_run:
        print(
            json.dumps(
                dict(policy_version=POLICY["version"], group=args.group, jobs=jobs),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_dir = DATA / "logs" / stamp
    lock = DATA / ".update.lock"
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        print(
            "Another update owns data/.update.lock; confirm it has stopped before removing the lock."
        )
        return 1
    os.close(fd)
    try:
        results = run_steps(steps, log_dir)
        checks = run_steps([("validate", ["scripts/validate.py"])], log_dir)
        results += checks
        if checks[0]["returncode"] == 0:
            results += run_steps(
                [
                    ("publish", ["scripts/build_web_data.py"]),
                    ("parquet", ["scripts/export_database.py"]),
                ],
                log_dir,
            )
        required = {"validate", "publish", "parquet"}
        publication_complete = {
            r["step"] for r in results if r["step"] in required and r["returncode"] == 0
        } == required
        report = dict(
            started_at=stamp,
            policy_version=POLICY["version"],
            offline=args.offline,
            group=args.group,
            steps=results,
            publication_complete=publication_complete,
            ok=all(r["returncode"] == 0 for r in results),
        )
        log_dir.mkdir(parents=True, exist_ok=True)
        (log_dir / "run.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        (DATA / "last_update.json").write_text(
            json.dumps(report, indent=2), encoding="utf-8"
        )
        return 0 if report["ok"] else 2
    finally:
        lock.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
