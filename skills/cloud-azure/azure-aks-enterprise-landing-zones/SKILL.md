---
name: azure-aks-enterprise-landing-zones
description: "Azure AKS enterprise landing zones: Azure CNI Overlay networking and IP planning, private clusters, Entra Workload Identity federation, Azure Policy for Kubernetes, and node-pool topology. Use when building or hardening AKS to an enterprise baseline, when AKS pods must authenticate to Key Vault or other Azure services without any stored secret, or when enforcing Kubernetes governance on Azure."
level: senior
tags: [azure, aks, cni, workload-identity, policy, cloud]
compatible_runtimes: [antigravity, claude, codex, cursor]
---

# Azure AKS Enterprise Landing Zone & Governance Architecture

## When to Use This Skill

**Triggers — load this skill when:**

- An AKS cluster must be built or hardened to an enterprise baseline
- Workloads need Entra ID access via Workload Identity instead of secrets
- Kubernetes governance must be enforced with Azure Policy

**Route elsewhere when:**

- Hub-spoke networking and platform services -> `azure-cloud-engineering-patterns`
- Chart authoring -> `helm-kubernetes-deployment`
- Multi-cluster reconciliation -> `gitops-multi-cluster-argo-flux`

## 1. Enterprise Terraform AKS Landing Zone Configuration

```hcl
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-prod-enterprise"
  location            = "eastus2"
  resource_group_name = "rg-production-compute"
  dns_prefix          = "aks-prod"
  kubernetes_version  = "1.29"

  default_node_pool {
    name                = "system"
    node_count          = 3
    vm_size             = "Standard_D4ds_v5"
    os_disk_type        = "Ephemeral"
    vnet_subnet_id      = "/subscriptions/.../subnets/aks-subnet"
    only_critical_addons_enabled = true
    zones               = ["1", "2", "3"]
  }

  identity {
    type = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks_identity.id]
  }

  network_profile {
    network_plugin      = "azure"
    network_plugin_mode = "overlay"
    ebpf_data_plane     = "cilium"
    load_balancer_sku   = "standard"
  }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true
  azure_policy_enabled      = true
}
```

---

## 2. Key Architecture Standards

- **Azure CNI Powered by Cilium**: High-performance eBPF-based data plane, network policy enforcement, and IP address conservation.
- **Entra ID Workload Identity**: Federate K8s Service Accounts directly to Azure Managed Identities without static client secrets.
- **System vs User Node Pool Separation**: Keep critical K8s control addons isolated on dedicated system node pools.

---

## 3. CNI Overlay Networking & Private Clusters

**Azure CNI Overlay** is the default choice for enterprise scale: pods get addresses from a
private overlay CIDR instead of consuming VNet address space, so a cluster no longer needs tens
of thousands of routable IPs. Nodes stay in the VNet; only nodes and Services consume VNet IPs.

| Mode | VNet IPs consumed | Direct pod addressability | Use when |
| --- | --- | --- | --- |
| CNI Overlay | Nodes + Services only | No (SNAT out of node IP) | Default; large or growing clusters |
| CNI (node subnet) | Every pod | Yes | Legacy peers must reach pods directly |
| Kubenet | Nodes only | No | Deprecated — do not start here |

```hcl
network_profile {
  network_plugin      = "azure"
  network_plugin_mode = "overlay"
  network_policy      = "cilium"
  pod_cidr            = "10.244.0.0/16"   # overlay, not from the VNet
  service_cidr        = "10.0.32.0/20"
  dns_service_ip      = "10.0.32.10"
}

private_cluster_enabled             = true       # API server has no public endpoint
private_cluster_public_fqdn_enabled = false
api_server_access_profile {
  authorized_ip_ranges = []                       # empty because access is private-only
}
```

A private cluster moves the API server behind a Private Endpoint, so CI runners and admin
tooling must reach it over the hub network (private DNS zone
`privatelink.<region>.azmk8s.io` linked to every VNet that resolves it). Plan that path before
enabling it — the usual failure is a working cluster nobody can reach. Keep system and user
node pools separate, taint the system pool, and pin the Kubernetes version per pool so upgrades
are staged rather than simultaneous.

---

## 4. Key Vault Access Without Stored Secrets

Workload Identity federates the pod's ServiceAccount token to Entra ID, so no secret, connection
string, or certificate is ever stored in the cluster:

```bash
az identity federated-credential create --name aks-payments   --identity-name id-payments --resource-group rg-platform   --issuer "$(az aks show -g rg-platform -n aks-prod --query oidcIssuerProfile.issuerUrl -o tsv)"   --subject "system:serviceaccount:prod-payments:payments" --audience api://AzureADTokenExchange

az role assignment create --assignee "$CLIENT_ID"   --role "Key Vault Secrets User"   --scope "/subscriptions/$SUB/resourceGroups/rg-platform/providers/Microsoft.KeyVault/vaults/kv-prod"
```

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: payments
  namespace: prod-payments
  annotations:
    azure.workload.identity/client-id: <client-id>
---
# Pod template
metadata:
  labels: { azure.workload.identity/use: "true" }
spec:
  serviceAccountName: payments
```

The federated subject pins the identity to one namespace **and** one ServiceAccount — the
control that stops any other pod in the cluster from requesting the same token. Use the Key
Vault CSI driver when the application must read files rather than call the SDK; avoid the
deprecated pod-managed identity (aad-pod-identity) in new clusters.
