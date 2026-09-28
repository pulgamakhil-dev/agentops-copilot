# Upstream API Timeout Incident Runbook

## Purpose

This runbook provides guidance for diagnosing pipeline failures caused by upstream API timeouts, connectivity problems, or temporary service unavailability.

## Symptoms

Common indicators include:

- Pipeline fails while requesting data from an upstream API.
- HTTP 408, 429, 500, 502, 503, or 504 responses occur.
- API requests exceed configured timeout limits.
- Connection or read timeout errors appear.
- Pipeline completes only after retry.
- Upstream dependency latency increases unexpectedly.

## Common Error Categories

Typical classifications include:

- UPSTREAM_TIMEOUT
- API_TIMEOUT
- CONNECTION_TIMEOUT
- SERVICE_UNAVAILABLE
- RATE_LIMITED

## Investigation Procedure

1. Identify the failed pipeline run and correlation ID.
2. Review the HTTP status code and timeout error.
3. Check whether the upstream service was available during the failure.
4. Compare API latency with recent successful pipeline runs.
5. Check retry attempts and retry intervals.
6. Determine whether rate limiting occurred.
7. Review whether other pipelines using the same dependency also failed.
8. Confirm network and authentication status.

## Root Cause Examples

Possible root causes include:

- Temporary upstream service outage.
- Increased API response latency.
- Network connectivity degradation.
- API rate limiting.
- Incorrect timeout configuration.
- Upstream service overload.
- Dependency maintenance or deployment.

## Recommended Remediation

For temporary upstream failures:

1. Confirm that the upstream service has recovered.
2. Retry the request using controlled retry policies.
3. Use exponential backoff where appropriate.
4. Avoid immediate repeated retries that may increase upstream load.
5. Rerun the failed pipeline after service recovery and approval.

For recurring timeout failures:

1. Review API latency trends.
2. Review timeout and retry configuration.
3. Coordinate with the upstream service owner.
4. Evaluate rate limits and request volume.
5. Determine whether circuit-breaker protection is appropriate.
6. Escalate recurring dependency instability.

## Validation After Recovery

After remediation:

- Confirm the upstream API responds successfully.
- Confirm the pipeline completes successfully.
- Verify records read and written.
- Review rejected records.
- Check pipeline duration.
- Verify whether an SLA breach occurred.
- Associate successful retries with the original incident.

## Escalation

Escalate when:

- Multiple pipelines are affected.
- The upstream service remains unavailable.
- Retries repeatedly fail.
- SLA impact becomes significant.
- Authentication or authorization failures are involved.
- Data completeness cannot be confirmed.

## Safety Controls

AgentOps Copilot may diagnose the failure and recommend retry or configuration changes.

It must not automatically change production timeout settings, credentials, retry policies, or execute production pipeline reruns without appropriate authorization and human approval.