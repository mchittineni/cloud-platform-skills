---
name: chaos-engineering-resilience-testing
description: "Chaos engineering practice: steady-state hypotheses tied to SLIs, blast-radius containment, pre-agreed abort criteria and automated rollback, fault injection with AWS FIS, Chaos Mesh or LitmusChaos, and GameDay facilitation that produces fixes. Use when a failover or redundancy claim has never actually been tested, when planning a GameDay or resilience exercise, or when deciding whether it is safe to inject failure into production and how to bound it."
level: senior
tags: [chaos-engineering, resilience, fault-injection, gameday, sre, reliability, aws-fis]
compatible_runtimes: [antigravity, claude, codex, cursor]
---

# Chaos Engineering and Resilience Testing

## When to Use This Skill

**Triggers — load this skill when:**

- A redundancy or failover claim exists on paper and has never been exercised
- A GameDay, resilience exercise, or failure-injection experiment is being planned
- Injecting failure into production is proposed and the blast radius must be bounded
- Incidents keep revealing dependencies nobody knew were hard requirements

**Route elsewhere when:**

- Restore, backup, and region-loss recovery drills -> `backup-and-disaster-recovery`
- Finding a throughput or latency ceiling under load -> `performance-load-testing`
- Designing the redundancy being tested -> `scalability-high-availability-patterns`
- Defining the SLIs the hypothesis measures against -> `sli-slo-error-budget-design`
- Running the incident an experiment escalates into -> `incident-management-and-postmortem`

## 1. An experiment without a hypothesis is an outage

Every experiment is written down before anything is injected, in this shape:

```yaml
experiment: checkout-survives-single-az-loss
steady_state:
  # Measured, not asserted. These are existing SLIs with existing dashboards.
  - metric: checkout_success_rate      # good events / valid events
    expected: ">= 99.5% over 5m"
  - metric: checkout_p99_latency_ms
    expected: "<= 800"
hypothesis: >
  Losing every checkout pod in eu-west-1a keeps success rate above 99.5% and p99 under 800ms,
  because two other zones hold sufficient warm capacity and the LB ejects failing targets
  within 30 seconds.
method:
  - terminate all checkout pods in eu-west-1a
blast_radius:
  scope: checkout service, one AZ, staging first then production
  traffic: 100% (this is a redundancy claim; a sample would not test it)
  duration: 10 minutes maximum
abort_criteria:            # ANY of these ends the experiment immediately
  - checkout_success_rate < 99.0% for 60s
  - checkout_p99_latency_ms > 2000 for 60s
  - error budget consumption for the period exceeds 5%
  - any customer-reported incident, related or not
rollback: scale the AZ back up; automated, tested, under 60 seconds
owner: "@payments-team"
observers: ["@sre-oncall", "@payments-oncall"]
```

If the steady state cannot be measured, stop. You will not be able to tell a successful experiment
from an outage, and the exercise becomes an argument about screenshots.

## 2. Bound the blast radius deliberately

| Dimension | First run | Escalation path |
| --- | --- | --- |
| Environment | Staging with production-shaped traffic | Production off-peak |
| Scope | One instance, one pod, one dependency | One AZ, then one region |
| Traffic share | 1% via header-routed cohort | 100% for redundancy claims |
| Duration | 60 seconds | Up to the abort window |
| Recovery | Manual, human at the keyboard | Automated and timed |

Two rules that keep this safe: **the abort must not depend on the thing being broken** — a kill
switch that reads a config service you just partitioned is not a kill switch — and **the experiment
runs with a human watching**, until its automated abort has been proven by deliberately tripping it.

## 3. Fault injection with a managed service

AWS FIS is the low-effort start on AWS: it holds the stop condition as a first-class object bound to
a CloudWatch alarm, so the abort criteria live in the experiment rather than in a runbook.

```json
{
  "description": "checkout-survives-single-az-loss",
  "targets": {
    "checkoutTasksAZ1": {
      "resourceType": "aws:ecs:task",
      "selectionMode": "ALL",
      "resourceTags": { "service": "checkout" },
      "filters": [
        { "path": "AvailabilityZone", "values": ["eu-west-1a"] }
      ]
    }
  },
  "actions": {
    "stopTasks": {
      "actionId": "aws:ecs:stop-task",
      "targets": { "Tasks": "checkoutTasksAZ1" }
    }
  },
  "stopConditions": [
    {
      "source": "aws:cloudwatch:alarm",
      "value": "arn:aws:cloudwatch:eu-west-1:111122223333:alarm/checkout-slo-burn-fast"
    }
  ],
  "roleArn": "arn:aws:iam::111122223333:role/fis-checkout-experiment",
  "tags": { "experiment": "checkout-az-loss", "owner": "payments-team" }
}
```

The FIS role is scoped by tag to the checkout service only. A chaos tool with broad permissions is
itself the largest single-blast-radius risk in the platform.

Chaos Mesh and LitmusChaos are the in-cluster equivalents when the fault is Kubernetes-shaped —
network latency, DNS failure, packet loss, pod kill:

```yaml
apiVersion: chaos-mesh.org/v1alpha1
kind: NetworkChaos
metadata:
  name: payments-dependency-latency
  namespace: staging
spec:
  action: delay
  mode: all
  selector:
    namespaces: [staging]
    labelSelectors: { app: checkout }
  direction: to
  target:
    mode: all
    selector:
      namespaces: [staging]
      labelSelectors: { app: payments-gateway }
  delay:
    latency: "400ms"
    jitter: "100ms"
  duration: "5m" # always set a duration: the cluster self-heals if the operator dies
```

Latency injection finds more real defects than termination does. Killing a pod tests the scheduler;
adding 400ms to a dependency tests every timeout, retry budget, connection pool, and circuit breaker
you have — which is where the actual bugs live.

## 4. The failure modes worth injecting, in order of yield

| Fault | What it usually exposes |
| --- | --- |
| Dependency latency (+300–500ms) | Missing timeouts, unbounded retries, pool exhaustion, retry storms |
| Dependency returns errors | Fallbacks that were never exercised; cache stampede on recovery |
| DNS failure | Clients that resolve once at startup and never again |
| Single pod or instance kill | Whether readiness and connection draining actually work |
| AZ loss | Warm capacity assumptions and cross-AZ retry cost |
| Certificate or token expiry | The renewal path nobody has run since setup |
| Clock skew | Token validation, distributed locks, TTL logic |
| Full disk on one node | Log rotation, spool handling, eviction behaviour |

## 5. A GameDay that produces fixes, not slides

1. **Two weeks before** — pick one hypothesis, write the experiment, name the owner and observers.
2. **One week before** — dry-run in staging; confirm the abort criteria fire when tripped on purpose.
3. **Day of** — announce in the incident channel, note the start time, inject, watch the SLI.
4. **During** — one scribe records timestamps: injection, first alert, first human action, recovery.
5. **Immediately after** — the gap between injection and _first alert_ is the most valuable number
   produced. It is the detection debt you did not previously know you had.
6. **Within a week** — file the fixes. An experiment whose findings do not become tickets was
   entertainment.

Success is not "nothing broke". Success is a validated hypothesis or a discovered defect. An
experiment that reveals a broken assumption before a customer does is the highest-value outcome.

## 6. Best practices and anti-patterns

**Do:**

- **Tie the hypothesis to an existing SLI** so the verdict is arithmetic, not opinion.
- **Test the abort path first**, deliberately, before relying on it.
- **Announce experiments and label the telemetry** with the experiment ID, so an unrelated real
  incident is not misdiagnosed as the experiment — and vice versa.
- **Run experiments when the error budget can afford them**, and stop when it cannot.
- **Re-run the experiment after the fix.** An unverified fix is a hypothesis.
- **Automate the ones that pass** into a recurring, low-blast-radius schedule so resilience does not
  regress silently.

**Do not:**

- **Inject failure in production first.** Earn it in staging, with the abort proven.
- **Run without pre-agreed abort criteria.** Deciding mid-experiment whether things are bad enough
  to stop is how an experiment becomes an incident.
- **Give the chaos tool broad IAM or cluster-admin.** Scope it by tag or label to its targets.
- **Skip the duration or TTL** on an injected fault; the operator can die holding the fault open.
- **Measure only whether the system recovered.** Also measure whether anyone was _told_ — silent
  recovery hides an alerting gap that will matter when recovery does not happen.
- **Call it chaos engineering when it is unannounced breakage.** Without a hypothesis, a bounded
  blast radius, and an abort criterion, it is an outage with a nicer name.
