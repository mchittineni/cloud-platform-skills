# Cloud FinOps Framework: Inform, Optimize & Operate

!!! info "Skill metadata"
    **Name** `finops-framework-inform-optimize-operate` · **Level** `senior` · **Tags** `finops` `cost-optimization` `tagging` `kubecost` `cloud-economics`

    "Cloud FinOps: the Inform, Optimize and Operate lifecycle, allocation tagging, showback and chargeback, unit economics, Kubernetes cost attribution with Kubecost and OpenCost, Savings Plans, Reserved Instances and CUD commitment modelling, and waste detection. Use when a cloud bill has jumped unexpectedly and the driver is unknown, when deciding whether to buy commitments, or when charging shared spend back to teams."

    Source: [`skills/08-finops-cloud-economics/finops-framework-inform-optimize-operate/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/08-finops-cloud-economics/finops-framework-inform-optimize-operate/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- Cloud spend must be allocated, attributed, or forecast credibly
- A right-sizing, waste-cleanup, or commitment-purchase decision is needed
- Unit economics (cost per request/tenant/feature) must be established

**Route elsewhere when:**

- Capacity and autoscaling design -> `scalability-high-availability-patterns`
- Cluster-level node efficiency -> `aws-eks-enterprise-patterns` / `gcp-gke-autopilot-multi-tenant`
- Efficiency vs delivery-throughput metrics -> `devops-metrics-dora-kpis`

## 1. The FinOps 3-Phase Lifecycle

```text
       +--------------+
       |   INFORM     |  -> Visibility, Cost Allocation, Unit Economics
       +------+-------+
              |
       +------v-------+
       |  OPTIMIZE    |  -> Right-sizing, Waste Reduction, Commitment Models
       +------+-------+
              |
       +------v-------+
       |  OPERATE     |  -> Continuous Governance, Automated Budget Alerts
       +--------------+
```

---

## 2. Mandatory Enterprise Tagging Strategy (IaC / Terraform)

Enforce default provider tags across all cloud resources to ensure $100\%$ cost attribution:

```hcl
provider "aws" {
  region = "us-east-1"
  default_tags {
    tags = {
      Environment     = "production"
      CostCenter      = "CC-4092"
      Owner           = "data-platform-team"
      Service         = "stream-processing"
      FinOpsManaged   = "true"
      BusinessUnit    = "E-Commerce"
    }
  }
}
```

---

## 3. High-Impact Cloud Cost Optimization Checklist

- **Orphaned Storage Cleanup**: Delete unattached EBS volumes, unreferenced Azure managed disks, and stale RDS/EBS snapshots.
- **Commitment Coverage Target**: Maintain $75\%-85\%$ coverage with Compute Savings Plans / Reserved Instances (RIs) for steady-state baselines.
- **Kubernetes Cost Allocation**: Deploy Kubecost / OpenCost to slice cluster costs down to namespaces, labels, and individual Pods.
- **Storage Lifecycle Policies**: Transition S3 / GCS buckets to Infrequent Access (IA) after 30 days and Glacier / Archive after 90 days.

---

## 4. Showback, Chargeback & Cost Spike Triage

| Model | What the team sees | When it fits |
| --- | --- | --- |
| **Showback** | Their cost, reported, not billed | Starting point; builds awareness without finance plumbing |
| **Chargeback** | Their cost, charged to their budget | Mature tagging + trusted allocation; real spend accountability |

Start with showback. Chargeback on top of unreliable allocation produces disputes about the
data instead of decisions about the spend.

**Shared cost is where showback loses credibility.** Decide and publish the rule before the
first report: split shared clusters, observability, and support by a measured driver (Kubecost
/ OpenCost namespace cost, request count, or storage GB), never evenly. Keep unallocatable
spend visible as its own line — a hidden 30% "platform" bucket destroys trust in the whole model.

**Cost spike triage, in order:**

1. **Scope it**: Cost Explorer / BigQuery billing export grouped by service, then by usage type,
   at daily granularity — one dimension at a time until the delta is a single line item.
2. **Date it**: align the step change against deploys, autoscaling events, and commitment
   expiries; a step means a change shipped, a ramp means growth or a leak.
3. **Name the driver**: NAT gateway or cross-AZ data transfer, log ingestion volume, orphaned
   volumes and snapshots, idle load balancers, a retry storm, or expired Savings Plan coverage.
4. **Decide**: fix the driver, or accept it and re-forecast — with a named owner and a date.

Commitment purchases come last, after the waste is removed: buying a three-year commitment on
an inefficient baseline locks in the inefficiency. Cover measured steady-state usage only
(typically 60–80%), and let elastic peaks run on demand or spot.

---

## 5. Commitment Instruments Compared

| Instrument | Cloud | Flexibility | Typical discount | Watch out for |
| --- | --- | --- | --- | --- |
| Compute Savings Plan | AWS | Any region, family, OS, and across EC2/Fargate/Lambda | ~20-30% | Lowest discount of the AWS options |
| EC2 Instance Savings Plan | AWS | Locked to family + region, size-flexible | ~30-40% | Family lock-in outlives most architectures |
| Reserved Instances (RI) | AWS, Azure | Standard RIs are family/region-locked; convertible RIs can be exchanged | ~30-55% | Standard RIs are only tradable on the marketplace |
| Reservations | Azure | Scope to subscription or shared; exchangeable | ~30-60% | Cancellation limits apply |
| **CUDs** (Committed Use Discounts) | GCP | Resource-based CUDs are region+family scoped; spend-based CUDs are broader | ~25-55% | Resource CUDs do not follow a migration to a new machine family |

Sequence that avoids locking in waste:

1. Remove waste first (idle, orphaned, over-provisioned) — commitments on inefficient baselines
   fund the inefficiency for three years.
2. Measure the trough, not the average: commit to the floor of steady-state usage, typically
   60-80% coverage, and leave peaks on demand or spot.
3. Prefer the flexible instrument (Compute Savings Plans, spend-based CUDs, convertible RIs)
   whenever an architecture change is plausible within the term.
4. Track coverage and utilisation monthly as two separate metrics; high coverage with low
   utilisation means the commitment is being wasted.
