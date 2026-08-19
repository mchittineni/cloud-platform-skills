# SRE Guide: SLI, SLO, SLA & Multi-Window Burn Rate Alerting

!!! info "Skill metadata"
    **Name** `sli-slo-error-budget-design` · **Level** `senior` · **Tags** `sre` `slo` `sli` `sla` `error-budget` `observability` `prometheus`

    "SLI, SLO and SLA design: indicator selection with explicit good-events and valid-events definitions, availability and latency target setting, error-budget accounting and freeze policy, and multi-window multi-burn-rate alerting. Use when defining reliability targets or an SLO target for a user-facing API or service, replacing noisy threshold alerts with burn-rate alerts, or governing releases against a spent budget."

    Source: [`skills/sre-slo-sla-observability/sli-slo-error-budget-design/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/sre-slo-sla-observability/sli-slo-error-budget-design/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A service needs SLIs and SLOs defined from real user journeys
- Noisy threshold alerts should become multi-window burn-rate alerts
- An error-budget policy must govern release or freeze decisions

**Route elsewhere when:**

- Collector, dashboard, and tracing plumbing -> `prometheus-grafana-otel-tracing`
- Host-level saturation alerting -> `infrastructure-host-monitoring`
- Delivery throughput metrics -> `devops-metrics-dora-kpis`

## 1. Core Terminology & Formula Matrix

$$\text{Error Budget} = 100\% - \text{SLO Target}$$

For a **99.9% SLO** over a 30-day rolling window:

- Total Allowable Downtime / Bad Requests = $0.1\%$ ($43.2$ minutes over $30$ days).

---

## 2. Multi-Window Multi-Burn-Rate Alerting Architecture

Google SRE recommends alerting on multiple burn rates to balance alert precision and recall:

| Alert Severity | Burn Rate | % Budget Consumed | Short Window | Long Window | Notification Target |
| --- | --- | --- | --- | --- | --- |
| **Page (P1)** | $14.4\times$ | $2\%$ in 1h (100% in 2 days) | 5 mins | 1 hour | PagerDuty / On-call |
| **Page (P2)** | $6\times$ | $5\%$ in 6h (100% in 5 days) | 30 mins | 6 hours | PagerDuty / On-call |
| **Ticket (P3)** | $1\times$ | $10\%$ in 3 days (100% in 30d) | 6 hours | 3 days | Jira / Slack Channel |

---

## 3. Prometheus / PromQL Production Multi-Window Alert

```yaml
groups:
  - name: slo_checkout_latency
    rules:
      - alert: CheckoutLatencySLOBurnRateHigh
        expr: |
          (
            sum(rate(http_request_duration_seconds_count{service="checkout",le="0.5",status="200"}[5m]))
            /
            sum(rate(http_request_duration_seconds_count{service="checkout"}[5m])) < 0.9856
          )
          and
          (
            sum(rate(http_request_duration_seconds_count{service="checkout",le="0.5",status="200"}[1h]))
            /
            sum(rate(http_request_duration_seconds_count{service="checkout"}[1h])) < 0.9856
          )
        for: 2m
        labels:
          severity: page
          tier: p1
        annotations:
          summary: "High 1h SLO burn rate (14.4x) on Checkout service"
          description: "Over 2% of 30-day error budget consumed within the last hour."
          runbook_url: "https://wiki.corp/runbooks/checkout-slo"
```

---

## 4. Good Events, Valid Events & the Budget Policy

An SLI is only unambiguous when written as a ratio of explicitly defined event sets:

```text
SLI = good events / valid events
```

- **valid events**: requests the service is accountable for — excludes health checks, excludes
  load-test traffic, includes every real user request that reached the edge.
- **good events**: valid events that met the quality bar — e.g. HTTP status not in 5xx **and**
  served in under 300 ms. State the latency bound inside the definition; "availability" without
  a latency clause silently passes requests that took 40 seconds.

```promql
# Availability SLI, 28-day rolling, explicit good/valid sets
sum(rate(http_requests_total{job="checkout",code!~"5..",path!="/healthz"}[28d]))
/
sum(rate(http_requests_total{job="checkout",path!="/healthz"}[28d]))
```

**The error budget policy is the part with teeth.** Agree it with the business _before_ the
budget is spent, and write down what changes automatically:

| Budget consumed | Consequence (pre-agreed, automatic) |
| --- | --- |
| < 50% | Normal delivery; ship freely |
| 50–90% | Reliability work is prioritised into the next sprint; risky migrations deferred |
| > 100% (exhausted) | **Feature freeze**: only reliability fixes and security patches ship until the trailing window recovers |
| Exhausted twice in a quarter | SLO or architecture is wrong — re-derive the objective with the product owner |

An SLO with no freeze condition is a dashboard, not an objective.

---

## 5. Anti-Patterns

| Anti-pattern | Why it fails in production |
| --- | --- |
| Setting the SLO at 99.99% because it sounds serious | An unreachable target is missed permanently, the error budget is always exhausted, and the freeze policy becomes something everyone ignores. Derive the target from measured performance and what users actually need. |
| Availability defined without a latency clause | A request served in 40 seconds counts as "good", so the SLO stays green through an outage users can plainly feel. Put the latency bound inside the good-events definition. |
| Measuring at the server, not the user's edge | Server-side metrics miss DNS, TLS, CDN and the failures that never reached your process — exactly the ones users report. Measure as close to the client as the architecture allows. |
| Health-check and synthetic traffic counted as valid events | Constant successful probes inflate the ratio and mask real user failures. Exclude probes explicitly from the valid-events set. |
| Alerting on the SLO threshold rather than burn rate | A threshold alert fires on every one-minute blip and stays silent through a slow burn that consumes the quarter's budget. Multi-window multi-burn-rate is the fix. |
| An error-budget policy with no pre-agreed consequence | If nothing changes when the budget is exhausted, the SLO is a dashboard. Agree the freeze condition with the business _before_ it is needed, when it is still an abstract discussion. |
| One SLO for a service with many journeys | Checkout and marketing pages average into a number that describes neither. Set SLOs per critical user journey. |
