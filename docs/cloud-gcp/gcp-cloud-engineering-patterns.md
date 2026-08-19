# GCP Enterprise Cloud Engineering & Organization Governance

!!! info "Skill metadata"
    **Name** `gcp-cloud-engineering-patterns` · **Level** `senior` · **Tags** `gcp` `google-cloud` `shared-vpc` `iam` `cloud-engineering`

    "GCP platform engineering: organization, folder and project hierarchy, Organization Policy constraints, Shared VPC, VPC Service Controls, IAM Workload Identity Federation, and BigQuery operations. Use when designing a Google Cloud resource hierarchy or network, letting GitHub Actions or another external CI deploy to GCP without a service account key, or building a data perimeter."

    Source: [`skills/cloud-gcp/gcp-cloud-engineering-patterns/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/cloud-gcp/gcp-cloud-engineering-patterns/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A GCP organization needs hierarchy, policy constraints, or Shared VPC design
- External CI or workloads need keyless access via Workload Identity Federation
- Data-perimeter controls (VPC Service Controls) must be planned

**Route elsewhere when:**

- GKE cluster and tenancy design -> `gcp-gke-autopilot-multi-tenant`
- Cross-cloud posture benchmarks -> `cloud-security-posture-cspm-cis`

## 1. GCP Organization Resource Hierarchy (Terraform)

```hcl
resource "google_folder" "department_folder" {
  display_name = "Core-Engineering"
  parent       = "organizations/123456789012"
}

resource "google_project" "production_project" {
  name       = "prod-workloads"
  project_id = "corp-prod-workloads-4092"
  folder_id  = google_folder.department_folder.name
  billing_account = "01ABCD-23EFGH-45IJKL"
}

# Enforce Organization Policy (e.g. restrict public IP on Compute Engine)
resource "google_organization_policy" "restrict_public_ip" {
  org_id     = "123456789012"
  constraint = "compute.vmExternalIpAccess"

  list_policy {
    deny {
      all = true
    }
  }
}
```

---

## 2. Best Practices & Anti-Patterns

- **Do**: Use Shared VPC to centralize network administration and firewall rules in a dedicated host project.
- **Do**: Bind Kubernetes Service Accounts to GCP Service Accounts using Workload Identity Federation instead of exporting JSON private keys.
- **Don't**: Avoid using the default Service Account (`{project_number}-compute@developer.gserviceaccount.com`) for production workloads.

---

## 3. Keyless CI with Workload Identity Federation & BigQuery Operations

**GitHub Actions to GCP with no service account key.** Exported SA keys are the most common GCP
credential leak; federation removes them entirely:

```bash
gcloud iam workload-identity-pools create github --location=global
gcloud iam workload-identity-pools providers create-oidc github-actions \
  --workload-identity-pool=github --location=global \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository_owner=='acme'"

gcloud iam service-accounts add-iam-policy-binding deployer@PROJECT.iam.gserviceaccount.com \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/NUM/locations/global/workloadIdentityPools/github/attribute.repository/acme/payments"
```

```yaml
permissions: { id-token: write, contents: read }
steps:
  - uses: google-github-actions/auth@v2
    with:
      workload_identity_provider: projects/NUM/locations/global/workloadIdentityPools/github/providers/github-actions
      service_account: deployer@PROJECT.iam.gserviceaccount.com
```

Always set `--attribute-condition` on the provider: without it, **any** GitHub repository in the
world can mint tokens for the pool.

**BigQuery platform operations.** Cost and governance are the same problem here:

```sql
-- Partitioned + clustered: scanned bytes, not stored bytes, drive the bill
CREATE TABLE analytics.events (
  event_ts TIMESTAMP, user_id STRING, event_type STRING, payload JSON
)
PARTITION BY DATE(event_ts)
CLUSTER BY event_type, user_id
OPTIONS (partition_expiration_days = 400, require_partition_filter = TRUE);
```

- `require_partition_filter = TRUE` makes an unbounded full-table scan impossible by accident.
- Set custom quotas per project and reservation-based (slot) pricing once on-demand spend is
  predictable; alert on `INFORMATION_SCHEMA.JOBS_BY_PROJECT` for queries above a byte threshold.
- Authorized views and column-level policy tags, inside a VPC Service Controls perimeter, are
  what keep analyst access from becoming an exfiltration path.
