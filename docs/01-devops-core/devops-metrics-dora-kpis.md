# DORA Metrics & Engineering Performance KPIs

!!! info "Skill metadata"
    **Name** `devops-metrics-dora-kpis` · **Level** `senior` · **Tags** `dora` `metrics` `kpis` `devops-core` `continuous-delivery` `analytics`

    "DORA metrics instrumentation: deployment frequency, lead time for changes, change failure rate, and time to restore, with PromQL dashboards, benchmark bands, and anti-gaming guidance. Use when measuring delivery performance, building an engineering-metrics dashboard, or diagnosing why throughput or stability is poor."

    Source: [`skills/01-devops-core/devops-metrics-dora-kpis/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/01-devops-core/devops-metrics-dora-kpis/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- Delivery performance must be measured or benchmarked against DORA bands
- A metrics dashboard needs concrete PromQL and data sources
- Leadership is asking for engineering-productivity evidence

**Route elsewhere when:**

- Reliability targets and error budgets -> `sli-slo-error-budget-design`
- Cost-per-unit and efficiency metrics -> `finops-framework-inform-optimize-operate`

## 1. The 4 Core DORA Metrics

| DORA Metric | Elite Performer | High Performer | Medium Performer | Low Performer |
| --- | --- | --- | --- | --- |
| **Deployment Frequency** | Multiple deploys/day | Once/day - once/week | Once/week - once/month | Less than once/month |
| **Lead Time for Changes** | < 1 hour | 1 day - 1 week | 1 week - 1 month | > 1 month |
| **Change Failure Rate** | 0% - 15% | 16% - 30% | 16% - 30% | 46% - 60% |
| **Time to Restore (MTTR)** | < 1 hour | < 1 day | 1 day - 1 week | > 1 week |

---

## 2. PromQL Queries for Real-Time DORA Dashboards

```promql
# 1. Deployment Frequency (Deployments per day over 7-day rolling window)
sum(rate(deployment_events_total{environment="production"}[7d])) * 86400

# 2. Change Failure Rate (Failed deploys / Total deploys)
sum(rate(deployment_events_total{status="failed",environment="production"}[30d]))
/
sum(rate(deployment_events_total{environment="production"}[30d])) * 100

# 3. Mean Time to Restore (MTTR in minutes)
avg_over_time(incident_duration_minutes{severity=~"SEV-1|SEV-2"}[30d])
```

---

## 3. Best Practices & Anti-Patterns

- **Do**: Automate DORA telemetry directly from GitHub Actions / GitLab CI webhooks and PagerDuty webhooks.
- **Don't**: Never use individual velocity metrics (like PR counts or lines of code) to grade individual engineers; optimize systemic flow and lead time.

---

## 4. Anti-Gaming Guardrails

Every DORA metric can be improved without improving anything real. Treat these as the
measurement contract:

| Metric | How it gets gamed | Guardrail |
| --- | --- | --- |
| Deployment Frequency | Splitting one release into many no-op deploys | Count deploys that change a running artifact digest |
| Lead Time for Changes | Opening the PR only once the work is finished | Measure from first commit on the branch, not PR open |
| Change Failure Rate | Not recording failures, or relabelling rollbacks as "planned" | Derive from rollback/hotfix events, not self-reported incident tickets |
| Time to Restore | Closing the incident before the fix ships | Clock stops at verified customer recovery |

Non-negotiables:

- **Never** attribute these metrics to individuals — they are system metrics; individual
  attribution reliably produces gaming instead of improvement.
- Always report throughput (frequency, lead time) **together with** stability (CFR, restore
  time). Either pair alone is trivially optimised at the other's expense.
- Pair the numbers with a qualitative signal (developer survey) before drawing conclusions.
