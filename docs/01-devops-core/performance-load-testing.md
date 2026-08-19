# Performance Engineering & Distributed Load Testing with k6

!!! info "Skill metadata"
    **Name** `performance-load-testing` · **Level** `mid` · **Tags** `performance` `load-testing` `k6` `locust` `benchmarking` `sre`

    "Performance engineering with k6 and Locust: load, stress, spike and soak profiles, virtual users (VUs), latency percentiles (p95/p99), threshold-gated tests in CI, and bottleneck profiling. Use when writing a k6 or Locust script, deciding whether an API can handle a peak traffic event, capacity planning before launch, or investigating why average latency looks fine while users report slowness."

    Source: [`skills/01-devops-core/performance-load-testing/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/01-devops-core/performance-load-testing/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A service needs a load, stress, spike, or soak profile authored and run
- You must set or verify latency/error thresholds as a release gate
- Capacity planning or a suspected regression needs measured evidence

**Route elsewhere when:**

- Turning measured latency into an SLO and error budget -> `sli-slo-error-budget-design`
- Autoscaling and failover architecture -> `scalability-high-availability-patterns`

## 1. Declarative k6 Load & Stress Test Script (`load_test.js`)

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 50 },  // Ramp up to 50 users
    { duration: '5m', target: 200 }, // Steady high load
    { duration: '2m', target: 500 }, // Stress spike
    { duration: '1m', target: 0 },   // Ramp down
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],         // Error rate must be < 1%
    http_req_duration: ['p(95)<250', 'p(99)<500'], // 95% < 250ms, 99% < 500ms
  },
};

export default function () {
  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer test-token-12345',
    },
  };
  
  const res = http.get('https://api.staging.internal/v1/catalog', params);
  check(res, {
    'status is 200': (r) => r.status === 200,
    'body has payload': (r) => r.body.length > 0,
  });
  sleep(1);
}
```

---

## 2. Best Practices & Anti-Patterns

- **Do**: Run baseline load tests in staging before every major architectural release or migration.
- **Do**: Pay attention to the p99 and p99.9 latency tail rather than average latency, which hides micro-bursts and lock contention.
- **Don't**: Never run uncoordinated load tests against production shared databases without circuit breakers and rollback plans.

---

## 3. Reading the Percentiles

| Statistic | What it hides | Use it for |
| --- | --- | --- |
| mean | Everything that matters; a bimodal distribution has no meaningful average | Capacity arithmetic only |
| p50 | The tail entirely | Sanity baseline |
| **p95** | The worst 1 in 20 requests | The usual SLO target and release gate |
| **p99** | Lock contention, GC pauses, cold caches | Tail-latency work, the metric users notice |
| p99.9 | Nothing — but is noisy at low request volume | Large-scale systems with enough samples |

A p95 threshold is what you gate a build on; a p99 regression is what you investigate. Report
both with the request count, since a percentile computed over 200 requests is not evidence.
Percentiles also do not average: never take the mean of per-instance p95 values — aggregate the
raw histogram (`histogram_quantile` over summed buckets) instead.

---

## 4. Virtual Users, Arrival Rate, and Locust

A **virtual user (VU)** is one concurrent synthetic client executing the script in a loop. VUs
are a concurrency model, not a request rate: 100 VUs against a 50 ms endpoint generate far more
load than 100 VUs against a 2 s endpoint. When the requirement is expressed in requests per
second, drive arrival rate directly instead:

```javascript
export const options = {
  scenarios: {
    steady_rps: {
      executor: 'constant-arrival-rate',
      rate: 500, timeUnit: '1s',        // 500 rps regardless of latency
      duration: '10m',
      preAllocatedVUs: 200, maxVUs: 1000,
    },
  },
};
```

**Locust** is the Python-native alternative — worth choosing when the load logic needs real
application libraries or a distributed master/worker fleet:

```python
from locust import HttpUser, task, between

class CatalogUser(HttpUser):
    wait_time = between(0.5, 2)

    @task(3)
    def browse(self):
        with self.client.get("/v1/catalog", name="/v1/catalog", catch_response=True) as r:
            if r.elapsed.total_seconds() > 0.5:
                r.failure("slower than 500ms SLO")
```

Both report percentiles; only k6 gates natively on thresholds, so Locust runs usually need an
explicit exit-code check in CI.
