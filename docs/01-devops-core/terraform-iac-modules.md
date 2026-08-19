# Production Terraform Infrastructure as Code Patterns

!!! info "Skill metadata"
    **Name** `terraform-iac-modules` · **Level** `mid` · **Tags** `terraform` `iac` `hcl` `automation` `devops-core`

    Terraform and OpenTofu module architecture, remote state with locking and encryption, provider and module version pinning, drift detection, and safe plan/apply workflow. Use when structuring or restructuring a Terraform repository across dev, staging and production environments, writing reusable modules, configuring a state backend, or investigating unexplained infrastructure drift.

    Source: [`skills/01-devops-core/mid-level-automation/terraform-iac-modules/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/01-devops-core/mid-level-automation/terraform-iac-modules/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- An IaC repository needs module boundaries, versioning, or directory structure decided
- Remote state must be configured with locking, encryption, and least-privilege access
- Drift, a dirty plan, or an unsafe apply needs diagnosis

**Route elsewhere when:**

- Multi-account DRY orchestration and policy gates -> `enterprise-iac-governance-terragrunt`
- Cloud-specific resource design -> the `aws-*`, `azure-*`, or `gcp-*` skills

## 1. Modular Directory Layout

```text
terraform/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── prod/
│       ├── main.tf
│       └── terraform.tfvars
└── modules/
    └── secure-vpc/
        ├── main.tf
        ├── variables.tf
        └── outputs.tf
```

---

## 2. Remote State Locking & Encryption Configuration

```hcl
terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "company-tfstate-production"
    key            = "networking/vpc/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}
```

---

## 3. Best Practices & Anti-Patterns

- **Do**: Maintain distinct state files per environment and per blast-radius tier (Network, Database, Compute, Apps).
- **Do**: Schedule automated `terraform plan -detailed-exitcode` checks in CI for drift detection.
- **Don't**: Never hardcode credentials in `.tf` files (`access_key` / `secret_key`); rely on OIDC or environment variables.
- **Don't**: Avoid monolithic single-state repositories that manage both foundation networking and application workloads in one state lock.

---

## 4. Terraform or OpenTofu

OpenTofu is the MPL-licensed fork of Terraform 1.5.x and remains configuration-compatible for
the patterns in this skill; the practical differences are licensing, registry defaults, and a
few post-fork features (OpenTofu state encryption, early variable evaluation).

```hcl
terraform {
  required_version = "~> 1.9"            # honoured by both binaries
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.60" }
  }
}
```

Migration is mechanical (`tofu init` against existing state), but pick one binary per repository
and pin it in CI — running `terraform` locally and `tofu` in the pipeline against shared state
invites provider-schema drift. Never mix the two against the same state file concurrently.
