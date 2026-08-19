# Google Kubernetes Engine (GKE) Autopilot Multi-Tenancy

!!! info "Skill metadata"
    **Name** `gcp-gke-autopilot-multi-tenant` · **Level** `senior` · **Tags** `gcp` `gke` `autopilot` `workload-identity` `vpc` `cloud`

    "GKE Autopilot and Standard multi-tenancy: namespace and node isolation, Workload Identity, network policy, Shared VPC topology, VPC Service Controls, and Autopilot vs Standard trade-offs. Use when designing a multi-tenant GKE platform, isolating tenant workloads, or choosing between Autopilot and Standard."

    Source: [`skills/06-cloud-gcp/gcp-gke-autopilot-multi-tenant/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/06-cloud-gcp/gcp-gke-autopilot-multi-tenant/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A GKE platform must isolate multiple teams or tenants safely
- Autopilot vs Standard must be chosen against workload constraints
- Pods need GCP API access via Workload Identity

**Route elsewhere when:**

- Organization-level hierarchy and policy -> `gcp-cloud-engineering-patterns`
- Cluster-agnostic packaging -> `helm-kubernetes-deployment`
- Tenant cost attribution -> `finops-framework-inform-optimize-operate`

## 1. Declarative GKE Multi-Tenant Cluster (Terraform)

```hcl
resource "google_container_cluster" "gke_autopilot" {
  name     = "gke-prod-autopilot"
  location = "us-central1"

  enable_autopilot = true
  network          = "projects/shared-vpc-host/global/networks/production-vpc"
  subnetwork       = "projects/shared-vpc-host/regions/us-central1/subnetworks/gke-subnet"

  ip_allocation_policy {
    cluster_secondary_range_name  = "gke-pods"
    services_secondary_range_name = "gke-services"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "10.0.0.0/8"
      display_name = "Corporate Internal Network"
    }
  }

  release_channel {
    channel = "REGULAR"
  }
}
```

---

## 2. GCP Security Baseline

- **GCP Workload Identity**: Map Kubernetes Service Accounts directly to GCP IAM Service Accounts via IAM Binding (`roles/iam.workloadIdentityUser`).
- **Binary Authorization**: Require cryptographic signatures on container images created through Google Cloud Build before admitting pods.
- **VPC Service Controls (VPC-SC)**: Place Cloud Storage, BigQuery, and Cloud SQL behind security perimeters to block data exfiltration.

---

## 3. Namespace Tenancy Controls

A tenant boundary is a **namespace plus four enforced controls**. A namespace alone isolates
names, nothing else.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tenant-payments
  labels: { tenant: payments, pod-security.kubernetes.io/enforce: restricted }
---
apiVersion: v1
kind: ResourceQuota          # 1. capacity: one tenant cannot starve the others
metadata: { name: tenant-quota, namespace: tenant-payments }
spec:
  hard:
    requests.cpu: "40"
    requests.memory: 160Gi
    limits.cpu: "80"
    persistentvolumeclaims: "20"
    count/services.loadbalancers: "2"
---
apiVersion: v1
kind: LimitRange             # 2. defaults: no unbounded pod inside the quota
metadata: { name: tenant-defaults, namespace: tenant-payments }
spec:
  limits:
    - type: Container
      default: { cpu: 500m, memory: 512Mi }
      defaultRequest: { cpu: 100m, memory: 128Mi }
      max: { cpu: "8", memory: 16Gi }
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy          # 3. network: default deny, then allow explicitly
metadata: { name: default-deny-all, namespace: tenant-payments }
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: { name: allow-same-tenant-and-dns, namespace: tenant-payments }
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
  ingress: [{ from: [{ podSelector: {} }] }]
  egress:
    - to: [{ podSelector: {} }]
    - to: [{ namespaceSelector: { matchLabels: { kubernetes.io/metadata.name: kube-system } } }]
      ports: [{ protocol: UDP, port: 53 }]
```

**4. RBAC** — bind tenant groups to a namespaced Role only — never a ClusterRole — and give each
tenant its own KSA bound to its own GSA, so cloud-side authorisation follows the same boundary.

For untrusted or multi-customer code, namespace isolation is not a security boundary: add
GKE Sandbox (gVisor) or separate node pools with taints, or give the tenant its own cluster.
