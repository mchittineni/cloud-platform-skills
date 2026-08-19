# Secrets Management with HashiCorp Vault & External Secrets Operator

!!! info "Skill metadata"
    **Name** `secrets-management-vault-kms` · **Level** `senior` · **Tags** `vault` `secrets` `kms` `kubernetes` `eso` `devsecops`

    "Secrets management with HashiCorp Vault, External Secrets Operator, and cloud KMS: dynamic short-lived credentials, envelope encryption, Kubernetes auth and workload identity, automatic rotation on a schedule instead of manual 90-day resets, and revocation under compromise. Use when a database password or API key sits in a plain Kubernetes Secret or a manifest checked into Git, or when workloads need credential material injected at runtime without storing it."

    Source: [`skills/devsecops-and-secops/secrets-management-vault-kms/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/devsecops-and-secops/secrets-management-vault-kms/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- Static long-lived credentials must be replaced with dynamic or short-lived ones
- Kubernetes workloads need secrets injected without committing them to Git
- A rotation policy or a leaked-credential response is being designed

**Route elsewhere when:**

- Detecting committed secrets in code -> `shift-left-security-sast-sca`
- Cloud IAM trust policy and federation design -> `aws-iam-zero-trust-policies`

## 1. External Secrets Operator (ESO) Pattern in Kubernetes

```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: vault-backend
  namespace: production
spec:
  provider:
    vault:
      server: "https://vault.internal.corp:8200"
      path: "secret"
      version: "v2"
      auth:
        kubernetes:
          mountPath: "kubernetes"
          role: "payment-service-role"
---
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: payment-db-credentials
  namespace: production
spec:
  refreshInterval: "1h"
  secretStoreRef:
    name: vault-backend
    kind: SecretStore
  target:
    name: db-credentials-k8s-secret
    creationPolicy: Owner
  data:
    - secretKey: DB_PASSWORD
      remoteRef:
        key: database/production/payment
        property: password
```

---

## 2. Secrets Management Principles

- **No Secrets in Git**: Enforce zero plain-text secrets in repository commits, even in private repositories.
- **Dynamic & Short-Lived Credentials**: Leverage Vault database engines to issue just-in-time PostgreSQL/MySQL credentials with 1-hour TTLs.
- **Envelope Encryption**: Encrypt sensitive data keys using Cloud KMS (AWS KMS, Azure Key Vault, GCP KMS) Customer Managed Keys (CMKs).

---

## 3. Workload Identity & Revocation

**Workload identity replaces the first secret.** Every secrets architecture bottoms out in one
question: how does the workload prove who it is without a pre-shared credential? Use the
platform's attested identity, never a bootstrap token in an image:

| Platform | Attested identity | Vault / cloud binding |
| --- | --- | --- |
| Kubernetes | Projected ServiceAccount token (OIDC) | Vault `kubernetes` auth role bound to SA + namespace |
| EKS | IRSA / Pod Identity | IAM role trust on the OIDC subject |
| AKS | Entra Workload Identity | Federated credential on the SA subject |
| GKE | Workload Identity | KSA→GSA binding |
| CI (GitHub/GitLab) | OIDC job token | Role trust conditioned on repo + ref + environment |

```yaml
# Vault Kubernetes auth role — identity is the namespace + service account, not a token
path "auth/kubernetes/role/payments" {
  bound_service_account_names      = ["payments"]
  bound_service_account_namespaces = ["prod-payments"]
  token_ttl                        = "20m"      # short TTL is the point
  token_policies                   = ["payments-read"]
}
```

**Revocation is the control that matters under compromise.** Design for it before the incident:

```bash
vault lease revoke -prefix database/creds/payments   # kill every dynamic credential at once
vault token revoke -accessor <accessor>              # kill one workload's session
aws iam update-access-key --status Inactive --access-key-id AKIA...   # static key: disable, then delete
```

Rotate on a schedule **and** on every role change or team departure; a rotation procedure that
has never been executed under time pressure is not yet a control. Static secrets that cannot be
made dynamic get a documented owner, a maximum age, and an alert when that age is exceeded.
