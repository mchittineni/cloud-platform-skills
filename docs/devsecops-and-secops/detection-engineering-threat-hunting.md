# Detection Engineering and Threat Hunting

!!! info "Skill metadata"
    **Name** `detection-engineering-threat-hunting` · **Level** `senior` · **Tags** `detection-engineering` `threat-hunting` `sigma` `mitre-attack` `siem` `detection-as-code` `secops`

    "Detection engineering and threat hunting: detection-as-code with Sigma rules in version control, log pipeline and telemetry source coverage, MITRE ATT&CK coverage mapping, alert precision and tuning to survive analyst trust, validation with Atomic Red Team, and hypothesis-driven hunts for activity that evaded automated controls. Use when security alerts are too noisy to act on, when deciding which detections to write and which telemetry to collect first, or when hunting for attacker activity nothing has alerted on."

    Source: [`skills/devsecops-and-secops/detection-engineering-threat-hunting/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/devsecops-and-secops/detection-engineering-threat-hunting/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- Security alerts are so noisy that analysts have stopped believing them
- New detections are needed and the question is which ones, in what order
- Telemetry coverage has to be justified: which log sources earn their ingest cost
- Attacker activity is suspected that no alert has fired on
- Detection content needs to live in version control with tests, not in a console

**Route elsewhere when:**

- A compromise is already confirmed and needs containment -> `secops-incident-triage-forensics`
- Container runtime rule syntax and tuning specifically -> `container-runtime-security-falco`
- Cloud misconfiguration and posture scanning -> `cloud-security-posture-cspm-cis`
- Coordinating the response process once an alert is real -> `incident-management-and-postmortem`
- Metrics, logs, and traces for reliability rather than security -> `prometheus-grafana-otel-tracing`

## 1. Detection as code, not console clicks

A detection that exists only in a SIEM UI has no history, no review, no tests, and no owner. Keep it
in Git in a vendor-neutral format and compile it to whatever backend you run.

```yaml
# detections/aws/iam_privilege_escalation_attach_admin.yml
title: IAM policy granting administrator access attached to a principal
id: 4b8d2b1e-6f4a-4c8f-9a0f-2f0a3d5c7e11
status: stable
description: >
  Detects attachment of AdministratorAccess (or a policy with wildcard action and resource)
  to a user, group, or role. This is the most common privilege-escalation step after an
  initial credential compromise.
references:
  - https://attack.mitre.org/techniques/T1098/
author: platform-security
date: 2026/08/19
logsource:
  product: aws
  service: cloudtrail
detection:
  selection:
    eventSource: iam.amazonaws.com
    eventName:
      - AttachUserPolicy
      - AttachRolePolicy
      - AttachGroupPolicy
    requestParameters.policyArn|endswith: "/AdministratorAccess"
  filter_break_glass:
    # Deliberate, reviewed exception. Owned and dated so it cannot rot silently.
    userIdentity.arn|contains: "role/break-glass-incident"
  condition: selection and not filter_break_glass
falsepositives:
  - Break-glass access during a declared incident (filtered above; alert separately on its use)
  - Initial account bootstrap by the landing-zone pipeline
level: high
tags:
  - attack.privilege_escalation
  - attack.t1098
```

```bash
# Compile the same rule to the backends you actually run
sigma convert -t splunk detections/aws/ -o out/splunk.conf
sigma convert -t esql   detections/aws/ -o out/elastic.esql

# CI: every rule must be schema-valid and must compile for every target backend
sigma check detections/
```

The value is not the format. It is that a detection now gets a pull request, a reviewer, a test, an
owner, and a diff when someone loosens it.

## 2. Coverage is a telemetry problem before it is a rule problem

You cannot detect what you do not collect. Map intended detections to sources first, and be honest
about the gaps.

| Attacker behaviour | Required telemetry | Common gap |
| --- | --- | --- |
| Credential use from an unexpected location | CloudTrail / Entra ID sign-in logs | Data-plane events (S3 object access) not enabled |
| Privilege escalation | CloudTrail management events, K8s audit log | K8s audit log disabled or not shipped |
| Container escape, in-pod shell | eBPF runtime sensor (Falco / Tetragon) | Runtime sensor absent on managed node pools |
| Persistence via CI | CI audit log, VCS audit log | CI logs retained 7 days, incident found on day 30 |
| Data staging and exfiltration | VPC flow logs, DNS query logs, egress proxy | DNS logging off; flow logs sampled |
| Lateral movement | Internal service mesh access logs | East-west traffic unlogged |

Then map to **MITRE ATT&CK** and publish the honest picture: a heat map claiming coverage for a
technique with one untested rule is worse than an empty cell, because it stops anyone looking.

Score each technique as **none / logged-only / detected / detected-and-tested**. Only the last one is
coverage.

## 3. Precision is the metric that keeps detections alive

Analyst trust is the scarcest resource in a security programme. A detection firing 200 times a week
with a 2% true-positive rate does not merely waste effort — it teaches everyone to close that alert
without reading it, including the week it is real.

```text
precision = true positives / (true positives + false positives)
```

| Precision | Route it to |
| --- | --- |
| > 0.9 | Page a human |
| 0.5 – 0.9 | Ticket queue for same-day triage |
| 0.1 – 0.5 | Hunt input or correlation signal only — never a page |
| < 0.1 | Not a detection. Fix it or delete it |

Tune with **context, not thresholds**. Raising a count threshold hides the attacker who does it
slowly. Better: add an identity dimension (is this principal _ever_ meant to do this?), a baseline
window (first time in 90 days), or a correlation requirement (this plus one other weak signal).

Track per rule, monthly: fires, confirmed true positives, precision, and time-to-triage. A rule with
zero fires in six months is either broken or covering something that no longer exists — validate it
or retire it. Silence is not evidence of safety.

## 4. Validate detections with real technique execution

An untested detection is a hypothesis about your log format.

```bash
# Atomic Red Team: execute one technique in a scoped, non-production account
Invoke-AtomicTest T1098.001 -CheckPrereqs
Invoke-AtomicTest T1098.001                # execute
Invoke-AtomicTest T1098.001 -Cleanup       # always clean up

# Then verify, and record the numbers that matter:
#   1. did the event reach the pipeline?      (collection works)
#   2. did the rule match it?                 (logic works)
#   3. how long from execution to alert?      (detection latency)
```

Detection latency is the number nobody measures and everybody needs: it is the floor on dwell time.
A perfect rule on a pipeline with a 40-minute batch delay is a 40-minute head start.

Run this in CI against recorded sample events so a log-schema change fails the build rather than
silently disabling the rule — schema drift is the most common way detections die quietly.

## 5. Hunting is for what the rules cannot express

Hunts are hypothesis-driven, time-boxed, and end in an artefact — a new detection, a coverage gap
filed, or a documented negative result.

```text
Hypothesis:  An attacker with a stolen CI token is using it outside pipeline hours.
Data:        90 days of CI audit logs joined to pipeline schedule metadata.
Method:      Token use grouped by principal and hour-of-day; flag any use with no
             corresponding pipeline run ID.
Outcome:     Either a finding, OR a new detection "CI token used with no pipeline run",
             OR a recorded negative result with the query saved for re-running.
```

Good hunt hypotheses come from: recent incidents (yours and public), techniques your ATT&CK map
scores as logged-only, assumptions in the architecture ("only CI can deploy"), and anomalies
analysts noticed but had nowhere to put.

A hunt that ends with "we looked and found nothing" and no saved query was a conversation. Save the
query; that is the deliverable.

## 6. Best practices and anti-patterns

**Do:**

- **Version, review, and test detections like application code** — including the tuning filters.
- **Give every filter an owner, a reason, and a date.** An unowned filter is how coverage silently
  disappears; review them on a schedule.
- **Alert on the absence of signal.** A log source that stops shipping should page, or an attacker
  who disables logging gets silence for free.
- **Write the triage step into the rule.** The first question an analyst will ask belongs in the
  detection, not in someone's memory.
- **Start from the techniques that fit your environment.** Kerberoasting detections do not help a
  cloud-native, identity-federated platform.
- **Separate detection from response severity.** A high-confidence low-impact alert is a ticket; a
  low-confidence high-impact one is a hunt, not a page.

**Do not:**

- **Buy coverage by importing every community rule.** Thousands of unvalidated rules produce noise
  that destroys trust in the ones that matter.
- **Tune by raising thresholds.** It hides slow attackers. Tune with identity and behavioural context.
- **Treat an empty ATT&CK cell as worse than a false one.** Overstated coverage is the more dangerous
  of the two, because it ends the investigation.
- **Ship a detection with no false-positive documentation.** The next analyst has to rediscover it at
  03:00.
- **Let a rule fire straight to a pager without a measured precision.** Page on evidence, not hope.
- **Hunt without a hypothesis.** Browsing dashboards is not hunting; it finds only what is already
  visible, which is the thing the detections were supposed to cover.
