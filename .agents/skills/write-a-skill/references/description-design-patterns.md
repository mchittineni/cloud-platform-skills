# Description Design Patterns & Triggers for Skills

The `description` in YAML frontmatter is the single most critical string in a skill definition. It serves as the routing index for LLMs.

## 1. The Anatomy of an Ideal Description

An effective description answers three questions in under 1024 characters:

1. **What does this skill do?** (3rd person summary)
2. **What tools / technologies are involved?**
3. **When should the agent trigger it?** (Explicit `"Use when..."` statement)

### ✅ Good Examples

```yaml
description: Configures production AWS EKS clusters with Karpenter node autoscaling, IRSA, and VPC CNI prefix delegation. Use when deploying Kubernetes on AWS or optimizing cluster compute costs.
```

```yaml
description: Triages compromised Linux and cloud infrastructure hosts, isolates network perimeters, and dumps volatile RAM forensics. Use when responding to active security incidents or compromised servers.
```

### ❌ Bad Examples

```yaml
# Bad: Uses first person, no triggers, too vague
description: I will help you write terraform code for your cloud.
```

```yaml
# Bad: Passive and lacks trigger conditions
description: Information about Kubernetes and pods.
```
