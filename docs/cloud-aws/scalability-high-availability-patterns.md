# Scalability & High Availability (HA) Architecture Patterns

!!! info "Skill metadata"
    **Name** `scalability-high-availability-patterns` · **Level** `senior` · **Tags** `scalability` `high-availability` `ha` `multi-az` `resilience` `cloud`

    "Scalability and high availability: multi-AZ and active-active topology, global load balancing and failover, HPA and KEDA autoscaling on custom or queue-depth metrics, circuit breakers, bulkheads, retries with jitter, and rate limiting. Use when a service must survive an availability zone failure, when it collapses under traffic spikes and drags downstream services with it, or when CPU is the wrong autoscaling signal."

    Source: [`skills/cloud-aws/scalability-high-availability-patterns/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/cloud-aws/scalability-high-availability-patterns/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A design must survive AZ or region loss without manual intervention
- Autoscaling on custom or event-driven metrics needs configuring
- Overload protection (circuit breaker, bulkhead, rate limit, backpressure) is missing

**Route elsewhere when:**

- Recovery from catastrophic loss -> `backup-and-disaster-recovery`
- Measuring headroom empirically -> `performance-load-testing`
- Mesh-level resilience policy -> `api-gateway-service-mesh`

## 1. High Availability Architecture Blueprint

```text
                      [Global Anycast / Route 53]
                                   |
                  +----------------+----------------+
                  |                                 |
           [Region 1 (Primary)]             [Region 2 (Secondary)]
                  |                                 |
         [Application Load Balancer]      [Application Load Balancer]
                  |                                 |
         +--------+--------+               +--------+--------+
         |        |        |               |        |        |
       [AZ-A]   [AZ-B]   [AZ-C]          [AZ-A]   [AZ-B]   [AZ-C]
         |        |        |               |        |        |
         +--------+--------+               +--------+--------+
                  |                                 |
        [Aurora Multi-AZ Primary] <------ [Aurora Global Read Replica]
```

---

## 2. Horizontal Pod Autoscaler (HPA) with Custom Metrics

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: payment-service-hpa
  namespace: production
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: payment-service
  minReplicas: 3
  maxReplicas: 30
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: 1k
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 100
          periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 300 # Prevent flapping
      policies:
        - type: Percent
          value: 10
          periodSeconds: 60
```

---

## 3. Best Practices & Anti-Patterns

- **Do**: Always distribute computing across a minimum of 3 Availability Zones (AZs) per region.
- **Do**: Use exponential backoff with jitter on all downstream API retries to prevent thundering herd crashes.
- **Don't**: Never scale down immediately without a stabilization window (`stabilizationWindowSeconds: 300`).

---

## 4. Event-Driven Autoscaling with KEDA

CPU is a poor proxy for demand in queue-driven and I/O-bound systems: the work is waiting in a
broker while CPU sits at 15%. KEDA scales on the backlog itself, and to zero when there is none.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: order-worker
spec:
  scaleTargetRef: { name: order-worker }
  minReplicaCount: 0            # scale-to-zero between bursts
  maxReplicaCount: 200
  pollingInterval: 15
  cooldownPeriod: 300
  advanced:
    horizontalPodAutoscalerConfig:
      behavior:
        scaleDown:
          stabilizationWindowSeconds: 300   # slow down, fast up
  triggers:
    - type: aws-sqs-queue
      metadata:
        queueURL: https://sqs.eu-west-1.amazonaws.com/1234/orders
        queueLength: "20"        # target backlog per replica
        awsRegion: eu-west-1
    - type: prometheus          # triggers compose; the highest demand wins
      metadata:
        serverAddress: http://prometheus.monitoring:9090
        query: sum(rate(orders_received_total[2m]))
        threshold: "50"
```

Choosing the signal: scale on **queue depth or lag** for async work (SQS, Kafka consumer lag,
RabbitMQ), on **in-flight requests or RPS** for synchronous services, and on CPU only for
genuinely CPU-bound compute. Always set `maxReplicaCount` below what the downstream datastore
can absorb — otherwise autoscaling converts a traffic spike into a database outage.
