# JOB Cleaner

## Usage

The Job cleaner services runs as a CRON job in the cluster. It removes the jobs of completed runs.

## Cleanup rule

* The job has a label `run_id`; and
* The run identify by the value of the `run_id` label is completed (the `status` of which is `Completed`).

## Schedule

The job runs daily at 22pm.