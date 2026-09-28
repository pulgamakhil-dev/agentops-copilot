# Spark Memory and Resource Exhaustion Runbook

## Purpose

This runbook provides guidance for diagnosing Spark pipeline failures caused by memory pressure, executor failures, skew, or insufficient compute resources.

## Symptoms

Common indicators include:

- Spark executors terminate unexpectedly.
- Out-of-memory errors occur.
- Executor lost messages appear.
- Tasks repeatedly retry.
- Pipeline duration increases significantly.
- Large shuffle operations occur.
- A small number of tasks run much longer than others.
- Pipeline fails during joins, aggregations, or large transformations.

## Common Error Categories

Typical classifications include:

- RESOURCE_EXHAUSTION
- OUT_OF_MEMORY
- EXECUTOR_FAILURE
- DATA_SKEW
- SHUFFLE_FAILURE

## Investigation Procedure

1. Identify the failed pipeline run and correlation ID.
2. Review Spark driver and executor logs.
3. Determine which stage or transformation failed.
4. Inspect executor memory usage.
5. Review shuffle read and write volume.
6. Check partition sizes and partition counts.
7. Identify skewed keys or unusually large partitions.
8. Review recent changes in input data volume.
9. Compare configuration with the last successful execution.

## Root Cause Examples

Possible root causes include:

- Executor memory is insufficient for the workload.
- Input data volume increased unexpectedly.
- Data skew creates oversized partitions.
- A large join causes excessive shuffle.
- Too few partitions concentrate data into large tasks.
- Cached datasets consume excessive executor memory.
- Inefficient transformations increase memory pressure.

## Recommended Remediation

For memory pressure:

1. Identify the stage consuming excessive memory.
2. Remove unnecessary caching or persistence.
3. Review executor memory configuration.
4. Reduce unnecessary intermediate data.
5. Repartition data when appropriate.
6. Test changes before applying them to production.

For data skew:

1. Identify high-frequency or skewed keys.
2. Review partition distribution.
3. Consider repartitioning or key-salting strategies.
4. Evaluate broadcast joins when the smaller dataset is appropriate.
5. Review Spark adaptive query execution behavior.

For large joins or shuffles:

1. Review join strategy and execution plan.
2. Filter unnecessary records before joining.
3. Select only required columns.
4. Review partitioning strategy.
5. Evaluate whether a broadcast join is safe and appropriate.

## Validation After Recovery

After remediation:

- Confirm the Spark job completes successfully.
- Review executor failures and task retries.
- Compare execution duration with previous runs.
- Check records read and written.
- Verify data quality checks.
- Confirm SLA status.
- Associate the successful retry with the original incident.

## Escalation

Escalate when:

- Executor failures continue after remediation.
- Data volume has changed significantly.
- Multiple Spark pipelines are affected.
- Cluster capacity is insufficient.
- Data loss or incomplete processing is suspected.
- Production infrastructure changes are required.

## Safety Controls

AgentOps Copilot may recommend Spark tuning or remediation strategies but must not automatically modify production cluster resources, Spark configuration, or pipeline code.

Infrastructure changes and production reruns require appropriate authorization and human approval.