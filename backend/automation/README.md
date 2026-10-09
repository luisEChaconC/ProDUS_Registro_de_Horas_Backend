# Automation runner

This directory provides controlled execution of backend automation jobs.

When a job is `ENABLED`, the runner registers it in `crontab` using its configured schedule.

## Structure

- `jobs/`: automation job scripts (`*.bash` or `*.sh`).
- `schedules/`: schedule for each job (`<job_name>.cron`, a five-field expression).
- `enabled/`: flags (`*.enabled`) indicating which jobs are active.
- `logs/`: activation and execution logs.
- `run_job.bash`: runs a specific job.
- `run_enabled.bash`: runs all enabled jobs.
- `enable_job.bash`: enables one job or all jobs.
- `disable_job.bash`: disables one job or all jobs.
- `list_jobs.bash`: displays the ENABLED/DISABLED status.
- `set_schedule.bash`: sets or updates a job's cron schedule.

## Quick start

From `backend/automation`:

```bash
./list_jobs.bash
./set_schedule.bash close_open_time_logs "0 0 * * *"
./enable_job.bash close_open_time_logs
./run_job.bash close_open_time_logs
./run_enabled.bash
./disable_job.bash close_open_time_logs
./enable_job.bash --all
./disable_job.bash --all
```

## Job schedules

Each job uses its own file in `schedules/`:

- `schedules/close_open_time_logs.cron` -> `0 0 * * *` (midnight)

Example for Wednesday at 7:00 AM:

```bash
./set_schedule.bash close_open_time_logs "0 7 * * 3"
```

## How is a job run automatically?

When `enable_job` is run, the script creates or updates a `crontab` entry for that job.

When `disable_job` is run, the script removes the job's cron entry.

`run_job` and `run_enabled` remain available for immediate manual execution.

## Cron (global alternative)

Run enabled jobs every day at midnight:

```cron
0 0 * * * cd /home/sebas-uwu/Desktop/Produs/ProDus_Registro_de_Horas_Backend/backend/automation && ./run_enabled.bash
```

## Logging

- General log: `logs/automation.log`
- Per-job log: `logs/<job_name>.log`
