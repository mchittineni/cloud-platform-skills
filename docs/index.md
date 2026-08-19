# Cloud & Platform Engineering Skills

38 production-grade skills for Cloud, Platform, SRE, Security and FinOps engineering — portable across Claude Code, Antigravity/Gemini CLI, Codex, Cursor and GitHub Copilot.

Each skill states its own activation triggers and, critically, when to route elsewhere. Load one skill, never the library.

## DevOps Core

| Skill | Level | Load when |
| --- | --- | --- |
| [backup-and-disaster-recovery](01-devops-core/backup-and-disaster-recovery.md) | senior | Use when designing a DR strategy, setting RPO/RTO targets, automating backups, or running a restore or failover exercise." |
| [cicd-pipeline-design](01-devops-core/cicd-pipeline-design.md) | mid | Use when a pipeline is slow because every job reinstalls dependencies, when long-lived AWS or cloud access keys stored as CI secrets must be removed, or when building, gating and speeding up a build-test-deploy workflow." |
| [configuration-management-ansible](01-devops-core/configuration-management-ansible.md) | mid | Use when applying a hardening or CIS baseline repeatably across many Ubuntu or RHEL hosts, refactoring a monolithic playbook into roles, or fixing a playbook that reports 'changed' on every run." |
| [database-devops-lifecycle](01-devops-core/database-devops-lifecycle.md) | senior | Use when adding, renaming or dropping a column on a large Postgres or MySQL table without downtime, running migrations from a deploy pipeline, or diagnosing read replicas lagging behind the primary and serving stale data." |
| [devops-metrics-dora-kpis](01-devops-core/devops-metrics-dora-kpis.md) | senior | Use when measuring delivery performance, building an engineering-metrics dashboard, or diagnosing why throughput or stability is poor." |
| [docker-containerization-basics](01-devops-core/docker-containerization-basics.md) | junior | Use when writing or reviewing a Dockerfile, shrinking image size, fixing slow builds, or hardening containers before they reach a registry." |
| [enterprise-iac-governance-terragrunt](01-devops-core/enterprise-iac-governance-terragrunt.md) | staff | Use when Terraform has been copy-pasted across many accounts or environments, or when non-compliant resources such as unencrypted or untagged S3 buckets must be blocked in CI before apply rather than found afterwards." |
| [git-branching-merge-strategies](01-devops-core/git-branching-merge-strategies.md) | junior | Use when choosing a branching model, defining merge/rebase rules for a team, resolving conflicts, or recovering from a bad commit, push, or revert. |
| [gitops-multi-cluster-argo-flux](01-devops-core/gitops-multi-cluster-argo-flux.md) | senior | Use when managing many clusters or environments declaratively, deciding how to structure repositories, branches and overlays to promote a release from staging to production, or debugging an Application stuck OutOfSync." |
| [helm-kubernetes-deployment](01-devops-core/helm-kubernetes-deployment.md) | mid | Use when authoring or reviewing a Helm chart, templating Kubernetes manifests, or debugging a failed or stuck Helm release." |
| [linux-sysadmin-troubleshooting](01-devops-core/linux-sysadmin-troubleshooting.md) | junior | Use when a server or VM is degraded, crawling, or unresponsive and needs live hands-on diagnosis, when writes fail with 'No space left on device' despite free space, or when a stuck process must be traced." |
| [performance-load-testing](01-devops-core/performance-load-testing.md) | mid | Use when writing a k6 or Locust script, deciding whether an API can handle a peak traffic event, capacity planning before launch, or investigating why average latency looks fine while users report slowness." |
| [scripting-and-automation](01-devops-core/scripting-and-automation.md) | mid | Use when writing, reviewing, or hardening an operational script, cron job, or internal CLI tool." |
| [terraform-iac-modules](01-devops-core/terraform-iac-modules.md) | mid | Use when structuring or restructuring a Terraform repository across dev, staging and production environments, writing reusable modules, configuring a state backend, or investigating unexplained infrastructure drift. |
| [zero-downtime-release-strategies](01-devops-core/zero-downtime-release-strategies.md) | senior | Use when releasing to a small percentage of traffic first while watching error rate and latency, when a bad deploy must roll back automatically without a human, or when choosing between canary, blue-green and rolling deployment." |

## DevSecOps & SecOps

| Skill | Level | Load when |
| --- | --- | --- |
| [cloud-security-posture-cspm-cis](02-devsecops-and-secops/cloud-security-posture-cspm-cis.md) | senior | Use when auditing an account or organization's security posture, finding unused and over-permissive permissions across hundreds of roles, preparing for a CIS or compliance review, or triaging misconfiguration findings." |
| [container-runtime-security-falco](02-devsecops-and-secops/container-runtime-security-falco.md) | senior | Use when alerting on attacker behaviour inside a running container such as an interactive shell being opened in production, writing or tuning a noisy Falco rule, or triaging a runtime alert." |
| [secops-incident-triage-forensics](02-devsecops-and-secops/secops-incident-triage-forensics.md) | staff | Use when a host, container or cloud credential is suspected compromised, when a leaked access key found in a public repository has already been used, or when capturing evidence." |
| [secrets-management-vault-kms](02-devsecops-and-secops/secrets-management-vault-kms.md) | senior | Use when a database password or API key sits in a plain Kubernetes Secret or a manifest checked into Git, or when workloads need credential material injected at runtime without storing it." |
| [shift-left-security-sast-sca](02-devsecops-and-secops/shift-left-security-sast-sca.md) | mid | Use when adding code, dependency or image scanning to a CI pipeline, when a scanner reports hundreds of findings that developers now ignore and gates need tuning for false positives, or when a customer or auditor asks for an SBOM produced by the build." |

## SRE & Observability

| Skill | Level | Load when |
| --- | --- | --- |
| [incident-management-and-postmortem](03-sre-slo-sla-observability/incident-management-and-postmortem.md) | staff | Use when running or improving incident response, declaring severity, coordinating an active outage, or writing a post-mortem." |
| [infrastructure-host-monitoring](03-sre-slo-sla-observability/infrastructure-host-monitoring.md) | mid | Use when standing up monitoring or dashboards across a fleet of nodes, authoring or tuning infrastructure alert rules, or arranging to be paged before a filesystem fills rather than after it is already full." |
| [prometheus-grafana-otel-tracing](03-sre-slo-sla-observability/prometheus-grafana-otel-tracing.md) | senior | Use when instrumenting services so a latency spike can be followed to the exact trace and log line, building the metrics-logs-traces stack, or fixing missing telemetry and cardinality blowups." |
| [sli-slo-error-budget-design](03-sre-slo-sla-observability/sli-slo-error-budget-design.md) | senior | Use when defining reliability targets or an SLO target for a user-facing API or service, replacing noisy threshold alerts with burn-rate alerts, or governing releases against a spent budget." |

## AWS

| Skill | Level | Load when |
| --- | --- | --- |
| [aws-cloud-migration-strategies](04-cloud-aws/aws-cloud-migration-strategies.md) | senior | Use when planning a datacenter exit or lease expiry, deciding whether a legacy monolith should be rehosted or refactored, or moving a large Oracle, SQL Server or Postgres database with minimal downtime." |
| [aws-eks-enterprise-patterns](04-cloud-aws/aws-eks-enterprise-patterns.md) | senior | Use when designing, scaling, hardening, or upgrading an EKS cluster, or fixing pod IP exhaustion and node-scaling problems." |
| [aws-iam-zero-trust-policies](04-cloud-aws/aws-iam-zero-trust-policies.md) | senior | Use when writing or reviewing an SCP or IAM policy, scoping down a role that has AdministratorAccess, or designing multi-account guardrails and federated access." |
| [scalability-high-availability-patterns](04-cloud-aws/scalability-high-availability-patterns.md) | senior | Use when a service must survive an availability zone failure, when it collapses under traffic spikes and drags downstream services with it, or when CPU is the wrong autoscaling signal." |

## Azure

| Skill | Level | Load when |
| --- | --- | --- |
| [azure-aks-enterprise-landing-zones](05-cloud-azure/azure-aks-enterprise-landing-zones.md) | senior | Use when building or hardening AKS to an enterprise baseline, when AKS pods must authenticate to Key Vault or other Azure services without any stored secret, or when enforcing Kubernetes governance on Azure." |
| [azure-cloud-engineering-patterns](05-cloud-azure/azure-cloud-engineering-patterns.md) | senior | Use when designing an Azure landing zone or network topology, making Storage, SQL or other PaaS unreachable from the internet, or enforcing tagging and allowed regions across every subscription." |

## GCP

| Skill | Level | Load when |
| --- | --- | --- |
| [gcp-cloud-engineering-patterns](06-cloud-gcp/gcp-cloud-engineering-patterns.md) | senior | Use when designing a Google Cloud resource hierarchy or network, letting GitHub Actions or another external CI deploy to GCP without a service account key, or building a data perimeter." |
| [gcp-gke-autopilot-multi-tenant](06-cloud-gcp/gcp-gke-autopilot-multi-tenant.md) | senior | Use when designing a multi-tenant GKE platform, isolating tenant workloads, or choosing between Autopilot and Standard." |

## Platform Engineering

| Skill | Level | Load when |
| --- | --- | --- |
| [api-gateway-service-mesh](07-platform-engineering/api-gateway-service-mesh.md) | senior | Use when configuring ingress routing, enforcing zero-trust service-to-service traffic, or debugging mesh routing and mTLS failures." |
| [cloud-native-microservices-patterns](07-platform-engineering/cloud-native-microservices-patterns.md) | senior | Use when pods are killed during a deploy and drop in-flight requests, when Kubernetes restarts a container that is merely slow to start, or when refactoring a service to run correctly on Kubernetes." |
| [internal-developer-portal-backstage](07-platform-engineering/internal-developer-portal-backstage.md) | staff | Use when building self-service so developers can create a new production-ready service in one click, defining golden paths, onboarding services into a catalog, or measuring platform adoption." |
| [serverless-event-driven-architecture](07-platform-engineering/serverless-event-driven-architecture.md) | senior | Use when designing event-driven flows, choosing FIFO versus standard for per-customer ordering at high throughput, or when events are lost, duplicated or throttled." |

## FinOps

| Skill | Level | Load when |
| --- | --- | --- |
| [finops-framework-inform-optimize-operate](08-finops-cloud-economics/finops-framework-inform-optimize-operate.md) | senior | Use when a cloud bill has jumped unexpectedly and the driver is unknown, when deciding whether to buy commitments, or when charging shared spend back to teams." |

## Productivity

| Skill | Level | Load when |
| --- | --- | --- |
| [write-a-skill](productivity/write-a-skill.md) | staff | Use when creating, refactoring, auditing, or reviewing an AI agent skill in this repository or any skills library." |

## Quality gates

Every skill passes four gates before merge — structure and mirror sync, offline routing and content-coverage evals, the 8-point compliance inspection, and generated-target freshness. See [CONTRIBUTING.md](https://github.com/mchittineni/cloud-platform-skills/blob/main/CONTRIBUTING.md).
