# Schema Drift Incident Runbook

## Purpose

This runbook provides operational guidance for diagnosing and recovering from data pipeline failures caused by unexpected source schema changes.

## Symptoms

Common indicators of schema drift include:

- Pipeline execution fails during ingestion or transformation.
- Expected columns are missing.
- New unexpected columns appear in the source.
- Column data types change.
- Required fields become nullable.
- Data quality validation fails.
- Source and target schemas no longer match.
- Record rejection counts increase unexpectedly.

## Common Error Categories

Typical classifications include:

- SCHEMA_DRIFT
- SCHEMA_MISMATCH
- MISSING_COLUMN
- UNEXPECTED_COLUMN
- DATA_TYPE_MISMATCH

## Investigation Procedure

1. Identify the failed pipeline run and correlation ID.
2. Compare the current source schema with the last successful execution.
3. Determine which columns were added, removed, renamed, or changed.
4. Review data quality validation results and rejected record counts.
5. Verify whether the schema change was expected and approved.
6. Check downstream transformations for dependencies on the changed fields.
7. Determine whether the target schema supports the new structure.

## Root Cause Examples

Possible root causes include:

- An upstream application deployed a schema change without notifying downstream teams.
- A source column was renamed or removed.
- A source data type changed.
- A previously optional field became required.
- A new nested structure was introduced.
- The ingestion contract and source schema became inconsistent.

## Recommended Remediation

For an expected schema change:

1. Validate the new schema against the approved data contract.
2. Update the ingestion mapping or transformation logic.
3. Update schema validation rules.
4. Test the change using representative source records.
5. Validate downstream compatibility.
6. Rerun the failed pipeline after approval.

For an unexpected schema change:

1. Do not automatically bypass schema validation.
2. Quarantine incompatible records when supported.
3. Notify the source-system owner.
4. Confirm whether the source should be rolled back or the pipeline updated.
5. Require human approval before changing production mappings.
6. Rerun the pipeline only after compatibility has been verified.

## Validation After Recovery

After remediation:

- Confirm the pipeline completes successfully.
- Compare records read and written.
- Review rejected record counts.
- Confirm data quality checks pass.
- Verify downstream tables contain expected fields.
- Confirm no unexpected SLA impact occurred.
- Associate the successful retry with the original incident.

## Escalation

Escalate the incident when:

- The schema change affects multiple downstream pipelines.
- Data loss or corruption is suspected.
- The source team cannot confirm the change.
- Production mappings require modification.
- Sensitive or regulated fields are affected.
- Multiple retries fail after remediation.

## Safety Controls

The AgentOps Copilot may recommend investigation and remediation steps, but it must not automatically modify production schemas, mappings, or pipeline configurations.

Production changes and pipeline reruns require appropriate authorization and human approval.