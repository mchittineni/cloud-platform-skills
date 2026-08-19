# Backup Strategies & Disaster Recovery (DR) Engineering

!!! info "Skill metadata"
    **Name** `backup-and-disaster-recovery` · **Level** `senior` · **Tags** `backup` `disaster-recovery` `rpo` `rto` `velero` `devops-core`

    "Backup and DR engineering: RPO/RTO tiering (backup-restore, pilot light, warm standby, multi-region active), cross-region replication, Velero Kubernetes backups, immutability/retention, and failover drills. Use when designing a DR strategy, setting RPO/RTO targets, automating backups, or running a restore or failover exercise."

    Source: [`skills/01-devops-core/backup-and-disaster-recovery/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/01-devops-core/backup-and-disaster-recovery/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- RPO/RTO targets must be set and priced against a DR tier
- Kubernetes or cloud workloads need automated, verified, immutable backups
- A failover drill, game day, or actual recovery is being planned or executed

**Route elsewhere when:**

- Live incident command during an outage -> `incident-management-and-postmortem`
- Multi-AZ/active-active steady-state resilience -> `scalability-high-availability-patterns`
- Database-level migration or PITR mechanics -> `database-devops-lifecycle`

## 1. RPO and RTO Metric Framework

$$\text{RPO (Data Loss Window)} \le 15\text{ minutes} \quad | \quad \text{RTO (Downtime Recovery)} \le 30\text{ minutes}$$

```text
+-------------------------------------------------------------------------------+
| DR Tier             | RTO / RPO        | Cost Profile | Implementation        |
+---------------------+------------------+--------------+-----------------------+
| Backup & Restore    | Hours / Days     | Lowest       | S3/GCS snapshots      |
| Pilot Light         | Tens of minutes  | Low-Medium   | Core DB live replica  |
| Warm Standby        | Minutes          | Medium-High  | Scaled-down replica   |
| Multi-Region Active | Seconds / Sub-sec| Highest      | Global Anycast/Spanner|
+-------------------------------------------------------------------------------+
```

---

## 2. Kubernetes Backup with Velero (`velero-schedule.yaml`)

```yaml
apiVersion: velero.io/v1
kind: Schedule
metadata:
  name: daily-prod-backup
  namespace: velero
spec:
  schedule: "0 2 * * *" # Daily at 02:00 UTC
  template:
    includedNamespaces:
      - production
      - istio-system
    snapshotVolumes: true
    ttl: "720h0m0s" # Retain 30 days
```

---

## 3. Best Practices & Anti-Patterns

- **Do**: Perform quarterly "Game Day" automated restore simulations; an untested backup is not a backup.
- **Do**: Store backup copies in an isolated, immutable (WORM / Object Lock) account to prevent ransomware tampering.
- **Don't**: Rely solely on disk snapshots for distributed databases without initiating proper database-consistent lock/flush mechanisms.

---

## 4. Restore Drill Protocol

An untested backup is a hypothesis. The only evidence of recoverability is a **restore drill**
with a measured outcome.

| Cadence | Drill | Evidence produced |
| --- | --- | --- |
| Weekly (automated) | Restore one random object/table into a scratch namespace, checksum it | Backups are readable and complete |
| Quarterly (tabletop + live) | Full application restore into an isolated environment | Measured RTO, gaps in runbooks |
| Annual (game day) | Region failover with real traffic cutover, unannounced to responders | Measured RPO/RTO under human conditions |

Run the drill against the documented runbook, not from memory, and record:

- wall-clock time to first byte served (actual RTO) versus the target;
- transaction loss window (actual RPO) versus the target;
- every manual step that was needed and is not yet automated.

A drill that ends with "we would have needed the person on leave" is a successful drill: it
found the dependency before the outage did. Restore drills must also verify immutability —
attempt the deletion of a locked backup and confirm the request is denied.
