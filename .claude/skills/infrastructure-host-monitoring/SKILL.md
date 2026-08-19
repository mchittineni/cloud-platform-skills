---
name: infrastructure-host-monitoring
description: "Fleet-wide infrastructure telemetry: node_exporter and cAdvisor collection with PromQL alert rules for CPU saturation, memory pressure, I/O wait, and disk-fill prediction using predict_linear. Use when standing up monitoring or dashboards across a fleet of nodes, authoring or tuning infrastructure alert rules, or arranging to be paged before a filesystem fills rather than after it is already full."
level: mid
tags: [monitoring, node-exporter, cadvisor, infrastructure, prometheus, sre]
compatible_runtimes: [antigravity, claude, codex, cursor]
---

# Infrastructure & Host Metrics Monitoring

## When to Use This Skill

**Triggers — load this skill when:**

- Node, VM, or bare-metal telemetry and alert rules need to be established
- You need proven PromQL for saturation, disk-fill, and I/O alerts
- A node is degraded and dashboards must show why

**Route elsewhere when:**

- Live hands-on-host diagnosis -> `linux-sysadmin-troubleshooting`
- Application-level SLOs -> `sli-slo-error-budget-design`
- Tracing and log pipelines -> `prometheus-grafana-otel-tracing`

## 1. Node Exporter & cAdvisor Essential PromQL Alerts

```yaml
groups:
  - name: host_infrastructure_alerts
    rules:
      - alert: HostHighCpuSaturation
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 85
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Host CPU saturation > 85% on {{ $labels.instance }}"

      - alert: HostDiskFillingFast
        expr: (node_filesystem_avail_bytes * 100) / node_filesystem_size_bytes < 15 and predict_linear(node_filesystem_avail_bytes[1h], 8 * 3600) < 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Host disk space on {{ $labels.instance }} will fill within 8 hours"

      - alert: ContainerMemoryThrottling
        expr: rate(container_cpu_cfs_throttled_periods_total[5m]) / rate(container_cpu_cfs_periods_total[5m]) > 0.25
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Container {{ $labels.container }} is experiencing > 25% CPU throttling"
```

---

## 2. Best Practices & Anti-Patterns

- **Do**: Use linear prediction (`predict_linear(...)`) to detect disk fill trends hours before an actual out-of-disk incident occurs.
- **Don't**: Never set static threshold alerts without an evaluation duration window (`for: 5m`) to avoid flapping false alarms during transient spikes.

---

## 3. Exporter Deployment & I/O Wait Alerts

```yaml
# node_exporter as a DaemonSet: host namespaces are required for real host metrics
args:
  - --path.rootfs=/host/root
  - --path.procfs=/host/proc
  - --path.sysfs=/host/sys
  - --collector.systemd
  - --no-collector.wifi
hostNetwork: true
hostPID: true
```

Run `node_exporter` on every node (DaemonSet or system package) and `cAdvisor`/kubelet for
container metrics. They answer different questions: `node_exporter` shows the host is
saturated; cAdvisor shows which container caused it.

```yaml
- alert: NodeHighIOWait
  expr: avg by (instance) (rate(node_cpu_seconds_total{mode="iowait"}[5m])) > 0.20
  for: 15m
  labels: { severity: warning }
  annotations:
    summary: "{{ $labels.instance }} spends >20% of CPU time in iowait"
    description: "Storage is the bottleneck, not CPU. Check device await via node_disk_io_time_weighted_seconds_total."

- alert: NodeDiskWillFillIn4Hours
  expr: predict_linear(node_filesystem_avail_bytes{fstype!~"tmpfs|overlay"}[6h], 4*3600) < 0
        and node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.30
  for: 30m
  labels: { severity: critical }
```

Alert on **trajectory** (`predict_linear`), not on a static 80% threshold: a disk at a steady
85% needs no page, and one at 40% falling fast needs one now. Every rule carries a `for:`
duration — without it, a single scrape blip pages a human.
