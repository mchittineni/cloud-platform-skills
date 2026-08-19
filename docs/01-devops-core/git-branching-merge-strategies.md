# Git Branching, Rebase & Release Strategies

!!! info "Skill metadata"
    **Name** `git-branching-merge-strategies` · **Level** `junior` · **Tags** `git` `version-control` `trunk-based-development` `devops-core`

    Git workflow selection (trunk-based, GitHub Flow, GitFlow), rebase vs merge policy, interactive rebase hygiene, conflict resolution, and emergency recovery operations. Use when choosing a branching model, defining merge/rebase rules for a team, resolving conflicts, or recovering from a bad commit, push, or revert.

    Source: [`skills/01-devops-core/junior-foundation/git-branching-merge-strategies/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/01-devops-core/junior-foundation/git-branching-merge-strategies/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A team needs a branching model chosen against its real deployment frequency
- You must define or enforce merge vs rebase and commit-hygiene policy in review
- Someone needs to undo, revert, stash, or recover work safely on a shared branch

**Route elsewhere when:**

- Pipeline triggers, gates, and required checks -> `cicd-pipeline-design`
- Git-as-source-of-truth for cluster state -> `gitops-multi-cluster-argo-flux`

## 1. Branching Strategy Selection

Choose the strategy appropriate for the team deployment frequency:

- **Trunk-Based Development (Recommended for CI/CD)**:
  - Short-lived feature branches (< 1-2 days).
  - Merged frequently into `main` via automated Pull Request checks.
  - Feature toggles (flags) used to hide incomplete features in production.
- **GitHub Flow**:
  - `main` is always deployable.
  - Feature branches branched off `main`, merged after code review and CI tests pass.

---

## 2. Rebase vs Merge Best Practices

### Clean Commit History via Interactive Rebase

```bash
# Keep feature branch up-to-date with main without merge bubbles
git checkout feature/auth-service
git fetch origin
git rebase origin/main

# Squash unneeded local micro-commits before opening PR
git rebase -i HEAD~4
```

### Safe Conflict Resolution

```bash
# In case of conflicts during rebase:
git status # identify conflicting files
# Edit conflicts, then:
git add <resolved-file>
git rebase --continue

# Abort cleanly if needed
git rebase --abort
```

---

## 3. Emergency Git Operations Runbook

```bash
# 1. Temporarily stash uncommitted changes with untracked files
git stash -u -m "WIP before hotfix switch"
git stash pop

# 2. Undo the last commit while keeping code changes staged
git reset --soft HEAD~1

# 3. Safely revert a faulty commit already pushed to main (creates inverse commit)
git revert <commit-sha>
```

---

## 4. Why Not GitFlow (Usually)

GitFlow's `develop` + `release/*` + long-lived `feature/*` model was designed for versioned
software shipped on a schedule to customers who install it. For a continuously deployed service
it adds two permanent merge fronts and delays integration, which is precisely where conflicts
and untested combinations accumulate.

| Model | Integration cadence | Fits |
| --- | --- | --- |
| Trunk-based (short-lived branches, <1 day) | Continuous | Continuous deployment, feature flags, high deploy frequency |
| GitHub Flow (branch + PR + deploy on merge) | Per PR | Most web services; the sensible default |
| GitFlow | Per release | Versioned/on-premise products with supported release lines and hotfix branches |
| Release branches only (`release/1.x`) | Per release line | Libraries and SDKs that must patch old majors |

If GitFlow is already in place and deploys are frequent, migrate incrementally: stop opening new
long-lived feature branches first, then collapse `develop` into `main` once the release cadence
is genuinely continuous. Adopting GitFlow because a diagram looked thorough is the anti-pattern.
