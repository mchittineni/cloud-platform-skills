# Azure Cloud Engineering & Secure Network Architecture

!!! info "Skill metadata"
    **Name** `azure-cloud-engineering-patterns` · **Level** `senior` · **Tags** `azure` `cloud-engineering` `virtual-wan` `private-endpoints` `devops`

    "Azure platform engineering: Cloud Adoption Framework management groups and subscription hierarchy, hub-and-spoke and Virtual WAN networking, Private Endpoints with Private DNS zones, Key Vault, Azure Policy as code, and Entra RBAC. Use when designing an Azure landing zone or network topology, making Storage, SQL or other PaaS unreachable from the internet, or enforcing tagging and allowed regions across every subscription."

    Source: [`skills/cloud-azure/azure-cloud-engineering-patterns/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/cloud-azure/azure-cloud-engineering-patterns/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- Subscription, management-group, or network topology must be designed on Azure
- PaaS services need private-only access via Private Endpoints and DNS
- Governance must be codified with Azure Policy and RBAC

**Route elsewhere when:**

- AKS-specific cluster design -> `azure-aks-enterprise-landing-zones`
- Cross-cloud posture auditing -> `cloud-security-posture-cspm-cis`
- Cost governance -> `finops-framework-inform-optimize-operate`

## 1. Hub-and-Spoke with Azure Private Endpoints & Virtual WAN

```hcl
resource "azurerm_private_endpoint" "sql_private_endpoint" {
  name                = "pe-sqldb-prod"
  location            = "eastus2"
  resource_group_name = "rg-networking-prod"
  subnet_id           = azurerm_subnet.private_endpoints_subnet.id

  private_service_connection {
    name                           = "psc-sqldb-prod"
    private_connection_resource_id = azurerm_mssql_server.sql_server.id
    subresource_names              = ["sqlServer"]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "pdzg-sqldb"
    private_dns_zone_ids = [azurerm_private_dns_zone.privatelink_database.id]
  }
}
```

---

## 2. Best Practices & Anti-Patterns

- **Do**: Enforce Private Endpoints for all PaaS services (Azure SQL, Cosmos DB, Key Vault, Storage Accounts).
- **Do**: Use Azure Policy definitions to deny resources without required tags or deployed in unauthorized regions.
- **Don't**: Never expose database management or RDP/SSH ports directly to public IP addresses without Azure Bastion.

---

## 3. Management Group Hierarchy & Private DNS

```text
Tenant Root Group
└── acme (top-level; all policy that must apply everywhere lands here)
    ├── platform
    │   ├── connectivity   # hub VNets, Virtual WAN, firewall, DNS resolver
    │   ├── identity       # domain controllers, Entra tooling
    │   └── management     # Log Analytics, automation, backup vaults
    ├── landing-zones
    │   ├── corp           # internal, private-only workloads
    │   └── online         # internet-facing workloads
    ├── sandbox            # loose policy, hard spend cap, no connectivity peering
    └── decommissioned     # deny-all-create policy, retained for audit
```

Assign policy at the **management group**, never per subscription: subscriptions move between
groups as workloads change, and inherited assignments follow automatically. Keep the hierarchy
shallow (three or four levels) — depth makes effective-policy debugging painful.

**Private DNS is where Private Endpoints actually fail.** The endpoint gets a private IP, but
callers keep resolving the public name unless every resolving VNet links the right zone:

| Service | Zone that must exist and be linked |
| --- | --- |
| Blob storage | `privatelink.blob.core.windows.net` |
| Azure SQL | `privatelink.database.windows.net` |
| Key Vault | `privatelink.vaultcore.azure.net` |
| AKS API | `privatelink.<region>.azmk8s.io` |

Centralise these zones in the connectivity subscription, link them to every spoke VNet, and
enforce automatic registration with the `Deploy-Private-DNS-Zones` policy initiative so a
developer creating a Private Endpoint cannot forget the DNS half. Diagnose with
`nslookup <resource>.blob.core.windows.net` from inside the spoke: a public IP in the answer
means the zone link, not the endpoint, is missing.

---

## 4. Cloud Adoption Framework Alignment

The hierarchy above is the Cloud Adoption Framework (CAF) enterprise-scale landing zone applied
concretely. CAF's value here is the separation it forces:

| CAF design area | Where it lands | Owned by |
| --- | --- | --- |
| Identity & access | `platform/identity` | Identity team |
| Network topology & connectivity | `platform/connectivity` hub, Virtual WAN, firewall, DNS | Network/platform team |
| Management & monitoring | `platform/management` Log Analytics, backup, automation | Platform team |
| Governance | Policy assignments at `acme` and per landing zone | Cloud governance |
| Application landing zones | `landing-zones/corp` and `landing-zones/online` subscriptions | Application teams |

Application teams own resources inside their subscription; they never own connectivity, policy,
or logging destinations. Deploy the baseline with the Azure Landing Zones Terraform/Bicep modules
rather than hand-built resource groups, so the hierarchy is reproducible and reviewable.
