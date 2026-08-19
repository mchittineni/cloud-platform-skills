# AWS IAM Zero-Trust Architecture & Service Control Policies (SCPs)

!!! info "Skill metadata"
    **Name** `aws-iam-zero-trust-policies` · **Level** `senior` · **Tags** `aws` `iam` `scp` `zero-trust` `security` `cloud`

    "AWS identity governance: Service Control Policies (SCPs) that deny actions organization-wide such as disabling CloudTrail or creating public S3 buckets, permission boundaries, ABAC tag-based access, condition keys, and cross-account role trust with ExternalId and OIDC. Use when writing or reviewing an SCP or IAM policy, scoping down a role that has AdministratorAccess, or designing multi-account guardrails and federated access."

    Source: [`skills/cloud-aws/aws-iam-zero-trust-policies/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/cloud-aws/aws-iam-zero-trust-policies/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- An IAM policy, SCP, or permission boundary must be authored or tightened
- Multi-account guardrails are needed across AWS Organizations
- Cross-account or federated role trust needs designing

**Route elsewhere when:**

- Detecting existing over-permissive access at scale -> `cloud-security-posture-cspm-cis`
- Application secret storage and rotation -> `secrets-management-vault-kms`
- Pod-level AWS access on EKS -> `aws-eks-enterprise-patterns`

## 1. Enterprise Service Control Policy (SCP) - Guardrail Baseline

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyDisablingSecurityServices",
      "Effect": "Deny",
      "Action": [
        "guardduty:DeleteDetector",
        "guardduty:DisassociateFromMasterAccount",
        "securityhub:DisableSecurityHub",
        "cloudtrail:DeleteTrail",
        "cloudtrail:StopLogging"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DenyUnapprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "cloudfront:*",
        "iam:*",
        "route53:*",
        "support:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2", "eu-west-1"]
        }
      }
    }
  ]
}
```

---

## 2. IAM Best Practices

- **Attribute-Based Access Control (ABAC)**: Authorize actions based on matching user tags with resource tags (`aws:PrincipalTag/Department` == `aws:ResourceTag/Department`).
- **Permission Boundaries**: Delegate IAM role creation to developers while attaching mandatory Permission Boundaries to prevent privilege escalation.
- **Short-Lived Sessions**: Enforce max 1-hour session duration on assumed roles.

---

## 3. Cross-Account Role Trust

Cross-account access is granted by the **trust policy**, and this is where over-permissive
wildcards do the most damage. Constrain the principal _and_ the conditions:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "CiDeployFromGitHubOIDC",
    "Effect": "Allow",
    "Principal": { "Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com" },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringEquals": { "token.actions.githubusercontent.com:aud": "sts.amazonaws.com" },
      "StringLike":   { "token.actions.githubusercontent.com:sub": "repo:acme/payments:environment:prod" }
    }
  }]
}
```

For third parties and vendors, require a confused-deputy guard:

```json
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::444455556666:root" },
  "Action": "sts:AssumeRole",
  "Condition": {
    "StringEquals":  { "sts:ExternalId": "acme-prod-7f3c1a" },
    "Bool":          { "aws:MultiFactorAuthPresent": "true" },
    "NumericLessThan": { "aws:MultiFactorAuthAge": "3600" }
  }
}
```

Rules:

- Never trust `"Principal": {"AWS": "*"}`, and never omit `sts:ExternalId` for a vendor role —
  without it, any other customer of that vendor can assume your role.
- Scope the OIDC `sub` to repository **and** ref/environment; `repo:acme/*` lets any branch of
  any repo in the org deploy to production.
- Set `MaxSessionDuration` to the shortest workable value and alias the role per use case, so
  CloudTrail shows _why_ a session existed, not just that it did.

---

## 4. Scoping Down an Over-Permissive Role

Removing `AdministratorAccess` blind breaks the workload. Derive the replacement from evidence:

```bash
# 1. What has this role actually used in 90 days?
aws iam generate-service-last-accessed-details --arn arn:aws:iam::1234:role/app-role
aws iam get-service-last-accessed-details --job-id <id> --query   'ServicesLastAccessed[?TotalAuthenticatedEntities>`0`].[ServiceNamespace,LastAuthenticated]'
# 2. Which exact API calls? (CloudTrail Lake or Athena over the trail)
# 3. Generate a candidate policy from observed calls
aws accessanalyzer start-policy-generation --policy-generation-details   '{"principalArn":"arn:aws:iam::1234:role/app-role"}' --cloud-trail-details file://trail.json
```

Then stage the change: attach the generated least-privilege policy **alongside** a permission
boundary first, watch `AccessDenied` in CloudTrail for a full business cycle (including
month-end jobs), and only then detach `AdministratorAccess`.

Guardrail example — deny public buckets and CloudTrail tampering organization-wide:

```json
{
  "Statement": [
    { "Sid": "DenyPublicS3", "Effect": "Deny",
      "Action": ["s3:PutBucketPublicAccessBlock", "s3:PutBucketAcl", "s3:PutBucketPolicy"],
      "Resource": "*",
      "Condition": { "StringNotEquals": { "aws:PrincipalArn": "arn:aws:iam::*:role/PlatformAdmin" } } },
    { "Sid": "ProtectTrail", "Effect": "Deny",
      "Action": ["cloudtrail:StopLogging", "cloudtrail:DeleteTrail", "cloudtrail:UpdateTrail"],
      "Resource": "*" }
  ]
}
```

An SCP does not grant anything — it only bounds what identity policies in the account can grant.
