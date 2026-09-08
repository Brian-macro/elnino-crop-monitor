"""Source checks due by configured cadence; failed checks wait for the next cadence."""

from datetime import date


def select_jobs(jobs, last_checked, today=None, group="all", due=False):
    today = date.fromisoformat(str(today or date.today())[:10])
    result = []
    for job in jobs:
        if group not in ("all", "scheduled", job["group"]):
            continue
        if due:
            checked = [last_checked.get(source) for source in job["sources"]]
            if all(checked) and all(
                (today - date.fromisoformat(str(stamp)[:10])).days
                < job["interval_days"]
                for stamp in checked
            ):
                continue
        result.append(job)
    return result
