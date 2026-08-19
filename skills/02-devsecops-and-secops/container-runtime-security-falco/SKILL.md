---
name: container-runtime-security-falco
description: "Runtime threat detection with Falco and eBPF: custom rule authoring, syscall and Kubernetes audit sources, macros, lists and exceptions for tuning, alert routing, and response playbooks. Use when alerting on attacker behaviour inside a running container such as an interactive shell being opened in production, writing or tuning a noisy Falco rule, or triaging a runtime alert."
level: senior
tags: [falco, runtime-security, ebpf, kubernetes, secops, devsecops]
compatible_runtimes: [antigravity, claude, codex, cursor]
---

# Runtime Security & Threat Detection with Falco and eBPF

## When to Use This Skill

**Triggers — load this skill when:**

- Runtime detection coverage is needed for containers or Kubernetes nodes
- A Falco rule must be written, scoped, or tuned against noise
- A runtime alert (shell in container, sensitive mount, crypto-miner) needs triage

**Route elsewhere when:**

- Pre-deploy image hardening -> `docker-containerization-basics`
- Full incident containment and forensics -> `secops-incident-triage-forensics`
- Cloud control-plane misconfiguration -> `cloud-security-posture-cspm-cis`

## 1. Custom Falco Security Rules (`falco_rules.local.yaml`)

```yaml
- rule: Terminal Shell Spawned Inside Production Container
  desc: Detect interactive shell execution (bash/sh) within production pods
  condition: >
    spawned_process and container
    and (k8s.ns.name = "production")
    and (proc.name in (bash, sh, zsh, ksh, csh))
    and not user_expected_debug_shell
  output: >
    CRITICAL: Shell spawned in container (user=%user.name pod=%k8s.pod.name
    ns=%k8s.ns.name image=%container.image.repository cmdline=%proc.cmdline)
  priority: CRITICAL
  tags: [container, mitre_execution, pci_dss]

- rule: Sensitive File Access Under /etc
  desc: Detect unexpected modification of system configuration files
  condition: >
    open_write and container
    and fd.name startswith "/etc"
    and not proc.name in (dpkg, apt, apk)
  output: >
    WARNING: File modified in /etc (file=%fd.name proc=%proc.name container=%container.name)
  priority: WARNING
  tags: [filesystem, mitre_persistence]
```

---

## 2. Runtime Security Operational Playbook

1. **Alert Routing**: Forward Falco alerts via Falcosidekick directly to Slack, PagerDuty, and SIEM (Elasticsearch/Splunk).
2. **Automated Containment**: Integrate Falco with Kubernetes webhook responders to isolate or terminate compromised pods automatically.
3. **Read-Only Root Filesystems**: Combine runtime monitoring with `readOnlyRootFilesystem: true` in Pod Security Standards.

---

## 3. Tuning: Macros, Lists & Exceptions

Noise is a security failure, not an inconvenience: a muted channel detects nothing. Tune by
narrowing the rule, never by disabling it.

```yaml
- list: trusted_debug_images
  items: ["company/debug-toolbox", "company/netshoot"]

- macro: from_trusted_debug
  condition: container.image.repository in (trusted_debug_images)

- rule: Terminal shell in container
  desc: A shell was spawned in a container outside the sanctioned debug path
  condition: >
    spawned_process and container and shell_procs
    and not from_trusted_debug
    and not k8s.ns.name in (kube-system, falco)
  output: "Shell in container (user=%user.name ns=%k8s.ns.name pod=%k8s.pod.name cmd=%proc.cmdline)"
  priority: WARNING
  tags: [container, shell, mitre_execution]
  exceptions:
    - name: ci_test_runner
      fields: [k8s.ns.name, proc.name]
      comps: [=, =]
      values: [[ci-runners, sh]]
```

Discipline that keeps the signal alive:

- Prefer `exceptions:` (structured, reviewable, per-field) over appending `and not ...` chains.
- Set `priority` so paging maps to CRITICAL/ERROR only; WARNING goes to a queue, not a pager.
- Review the top five noisiest rules weekly; a rule firing hundreds of times a day is either
  mis-scoped or describes normal behaviour that should be fixed at the source.
