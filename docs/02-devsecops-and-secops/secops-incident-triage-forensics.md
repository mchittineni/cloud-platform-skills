# SecOps Security Incident Triage & Compromise Containment

!!! info "Skill metadata"
    **Name** `secops-incident-triage-forensics` · **Level** `staff` · **Tags** `secops` `incident-response` `forensics` `threat-hunting` `soc`

    "Security incident response: compromise triage, cloud instance and credential containment, forensic disk and memory capture with chain of custody, IAM session and key revocation, and SIEM correlation for threat hunting. Use when a host, container or cloud credential is suspected compromised, when a leaked access key found in a public repository has already been used, or when capturing evidence."

    Source: [`skills/02-devsecops-and-secops/secops-incident-triage-forensics/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/02-devsecops-and-secops/secops-incident-triage-forensics/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A host, container, or credential is suspected compromised and must be contained
- Forensic evidence must be captured without destroying it
- Log/SIEM correlation is needed to scope attacker activity

**Route elsewhere when:**

- Availability-only outage with no security dimension -> `incident-management-and-postmortem`
- Detection rule authoring -> `container-runtime-security-falco`
- Post-incident hardening of posture -> `cloud-security-posture-cspm-cis`

## 1. Cloud Instance Compromise Triage Flow

```text
[Security Alert: Unauthorized C2 Traffic]
                    |
      1. Isolate Network (Do NOT power off)
                    |
      2. Snapshot Volatile Memory & EBS/Disks
                    |
      3. Revoke IAM Tokens & Rotate Credentials
                    |
      4. Forensic Analysis & Root Cause Determination
```

---

## 2. Emergency Cloud Containment Commands (AWS)

```bash
# 1. Attach Quarantine Security Group (Deny All Ingress / Egress)
aws ec2 modify-instance-attribute \
  --instance-id i-0123456789abcdef0 \
  --groups sg-0quarantine-isolate

# 2. Snapshot Root EBS Volume for Forensic Analysis
aws ec2 create-snapshot \
  --volume-id vol-0123456789abcdef0 \
  --description "FORENSIC-SNAPSHOT-INCIDENT-2026-08-19" \
  --tag-specifications 'ResourceType=snapshot,Tags=[{Key=ChainOfCustody,Value=IncidentResponse}]'

# 3. Revoke active AWS IAM Session / Role Credentials
aws iam put-role-policy \
  --role-name CompromisedServiceRole \
  --policy-name DenyAllExceptIR \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}]
  }'
```

---

## 3. Forensics Best Practices

- **Preserve Volatile Memory**: Do not reboot or terminate the instance before dumping RAM if rootkit investigation is required.
- **Maintain Chain of Custody**: Cryptographically hash (`sha256sum`) all forensic disk images and logs upon creation.
- **Out-of-Band Communication**: Conduct high-severity incident communication in dedicated, access-restricted out-of-band channels.
