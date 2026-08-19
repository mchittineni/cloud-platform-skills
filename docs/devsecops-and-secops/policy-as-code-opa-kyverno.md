# Policy as Code: Kyverno, OPA/Gatekeeper, and Conftest

!!! info "Skill metadata"
    **Name** `policy-as-code-opa-kyverno` · **Level** `senior` · **Tags** `policy-as-code` `kyverno` `opa` `gatekeeper` `conftest` `governance` `kubernetes`

    "Policy as code for Kubernetes and infrastructure: authoring Kyverno ClusterPolicy rules, OPA Rego in a Gatekeeper ConstraintTemplate, and Conftest checks, plus Pod Security Standards enforcement, policy unit testing, and an owned exception register with expiry dates. Use when privileged containers or pods without resource limits must be rejected at admission rather than reported, when admission policies need tests so a rule cannot silently stop matching, or when choosing between Kyverno and OPA Gatekeeper."

    Source: [`skills/devsecops-and-secops/policy-as-code-opa-kyverno/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/devsecops-and-secops/policy-as-code-opa-kyverno/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- Privileged containers, missing limits, or untagged resources must be blocked, not reported
- Admission policies need unit tests, because an untested rule silently stops matching
- Kubernetes needs Pod Security Standards enforced with real exceptions for real workloads
- Kyverno versus OPA/Gatekeeper has to be decided for a platform

**Route elsewhere when:**

- Verifying image signatures and provenance specifically -> `supply-chain-security-slsa-sigstore`
- Cloud account posture scanning after the fact -> `cloud-security-posture-cspm-cis`
- Terraform repository layout and module structure -> `terraform-iac-modules`
- Multi-account IaC governance and CI gating at scale -> `enterprise-iac-governance-terragrunt`
- Runtime behaviour detection rather than admission -> `container-runtime-security-falco`

## 1. Start with Pod Security Standards, then add policy for what they miss

Pod Security Admission is built in, costs nothing, and covers most container-hardening rules. Use it
as the baseline and reserve a policy engine for what PSA cannot express.

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: production
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/enforce-version: v1.34
    pod-security.kubernetes.io/warn: restricted # surfaces future tightening before it blocks
```

PSA cannot do cross-object rules, mutation, image-registry allowlists, or anything referencing
another resource's state. That is what Kyverno and Gatekeeper are for.

## 2. Kyverno: validate, mutate, and generate in YAML

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: require-resources-and-probes
  annotations:
    policies.kyverno.io/severity: medium
spec:
  validationFailureAction: Audit # Audit -> measure -> Enforce. Never Enforce first.
  background: true # also evaluate existing resources, to size the blast radius
  rules:
    - name: require-limits
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaces: [production, staging]
      exclude:
        any:
          - resources:
              namespaces: [kube-system] # cluster components predate your policy
      validate:
        message: >-
          Every container needs cpu/memory requests and a memory limit.
          Unbounded pods are the usual cause of node-level OOM cascades.
        pattern:
          spec:
            containers:
              - resources:
                  requests:
                    cpu: "?*"
                    memory: "?*"
                  limits:
                    memory: "?*"
```

Kyverno's advantage is that policy is Kubernetes YAML, so the whole team can read it. Its `mutate`
rules (`patchStrategicMerge`, e.g. forcing `automountServiceAccountToken: false`) and `generate`
rules also fix problems rather than only rejecting them.

## 3. OPA/Gatekeeper: Rego when the logic is genuinely conditional

```rego
package k8srequiredlabels

import future.keywords.in

violation[{"msg": msg}] {
  # Only production workloads need a cost-allocation owner
  input.review.object.metadata.namespace == "production"
  required := {"owner", "cost-center"}
  provided := {k | some k, _ in input.review.object.metadata.labels}
  missing := required - provided
  count(missing) > 0
  msg := sprintf("production workloads must carry labels: %v", [missing])
}
```

That Rego is delivered as a Gatekeeper `ConstraintTemplate` (which defines a `K8sRequiredLabels` CRD),
then instantiated per scope by a `Constraint` — the two-object split is what lets one policy be
enforced with different parameters per namespace.

**Choosing between them:**

| Need | Choose |
| --- | --- |
| Policy the team reads and writes without learning a language; mutation, generation, image verification | Kyverno |
| Conditional logic and set arithmetic; one language shared across Kubernetes, Terraform and API authorization | OPA/Gatekeeper |

Do not run both engines for overlapping concerns. Two admission webhooks with different verdicts is
a debugging problem nobody wants at 03:00.

## 4. Shift the same rules left: Conftest on the Terraform plan

Blocking at admission is too late for infrastructure: by then the bucket exists. Gate the plan.

```rego
# policy/terraform/s3.rego
package main

deny[msg] {
  r := input.resource_changes[_]
  r.type == "aws_s3_bucket"
  not r.change.after.tags.owner
  msg := sprintf("%s: missing required tag 'owner'", [r.address])
}
```

Inspect `r.change.actions` the same way to block _removals_ — a rule that only checks the final
state will happily allow encryption to be deleted.

```bash
terraform plan -out=tfplan
terraform show -json tfplan > tfplan.json
conftest test --policy policy/terraform tfplan.json   # non-zero exit fails the pipeline
```

Test the policies themselves — a guardrail with no test is a guardrail that silently stops matching.
`conftest verify --policy policy/terraform` runs `test_*` rules from `*_test.rego`, and
`kyverno test ./policies` asserts expected results per resource fixture. Both belong in CI.

## 5. Exceptions are the part everyone gets wrong

A policy with no exception mechanism gets disabled the first time it blocks something urgent. Give
exceptions a structure that expires.

```yaml
apiVersion: kyverno.io/v2
kind: PolicyException
metadata:
  name: legacy-batch-privileged
  namespace: batch
  annotations:
    owner: "@platform-team"
    expires: "2026-11-30" # a gate in CI fails the build once this date passes
    reason: "Vendor agent requires CAP_SYS_ADMIN. Replacement tracked in PLAT-1841."
spec:
  exceptions:
    - policyName: disallow-privileged-containers
      ruleNames: ["privileged-containers"]
  match:
    any:
      - resources: { kinds: [Pod], namespaces: [batch], names: ["legacy-agent-*"] }
```

Every exception needs an **owner**, an **expiry**, and a **reason**. Enforce that with a CI check
over the exception directory — an expired exception is a build failure, not a stale file nobody
reviews.

## 6. Best practices and anti-patterns

**Do:**

- **Roll out in three stages:** `Audit` with `background: true` to find existing violations, fix or
  except them, then `Enforce`.
- **Scope policies to namespaces and exclude cluster components.** A cluster-wide `Enforce` policy
  that matches `kube-system` can prevent the cluster from recovering after a reboot.
- **Set `failurePolicy: Ignore` while piloting**, and only move to `Fail` once the webhook's
  availability and latency are proven. A `Fail` webhook that is down blocks every deployment.
- **Write the message for the developer who will hit it** — say what to change, not which rule fired.
- **Version and test policies like code**, with `conftest verify` and `kyverno test` in CI.

**Do not:**

- **Enforce on day one.** The first policy is always broader than you think.
- **Duplicate the same rule in two engines.** Pick one enforcement point per concern.
- **Write policy that reaches the network.** Admission is on the request path; an external lookup
  turns a policy engine into a latency and availability dependency for every deploy.
- **Grant blanket namespace exclusions** as a shortcut. `production` excluded "temporarily" is how a
  guardrail quietly stops covering the thing it existed for.
- **Rely on admission alone.** It only sees create and update, so a policy added later leaves
  existing violations running — that is what `background: true` and a periodic report are for.
