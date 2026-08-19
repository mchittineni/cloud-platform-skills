# Enterprise CI/CD Pipeline Architecture

!!! info "Skill metadata"
    **Name** `cicd-pipeline-design` · **Level** `mid` · **Tags** `cicd` `github-actions` `gitlab-ci` `automation` `devops-core`

    "CI/CD pipeline architecture for GitHub Actions and GitLab CI: matrix testing, dependency caching, OIDC keyless cloud authentication, security gating, artifact provenance and attestation. Use when a pipeline is slow because every job reinstalls dependencies, when long-lived AWS or cloud access keys stored as CI secrets must be removed, or when building, gating and speeding up a build-test-deploy workflow."

    Source: [`skills/01-devops-core/mid-level-automation/cicd-pipeline-design/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/01-devops-core/mid-level-automation/cicd-pipeline-design/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A new pipeline is being authored, or an existing one is slow, flaky, or ungated
- Static cloud keys in CI must be replaced with OIDC short-lived credentials
- Release artifacts need provenance, signing, or attestation

**Route elsewhere when:**

- Deployment/rollout mechanics after the artifact is built -> `zero-downtime-release-strategies`
- Cluster reconciliation from Git rather than pipeline push -> `gitops-multi-cluster-argo-flux`
- Scanner selection and gate thresholds -> `shift-left-security-sast-sca`

## 1. GitHub Actions Production Standard Pipeline

```yaml
name: CI/CD Production Pipeline

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

permissions:
  contents: read
  security-events: write
  packages: write
  id-token: write # OIDC for Cloud authentication

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-and-test:
    name: Lint & Unit Tests
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Run Linters & Tests
        run: |
          pip install ruff pytest pytest-cov
          ruff check .
          pytest --cov=src --cov-report=xml

  security-scan:
    name: SAST & Dependency Vulnerability Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy Vulnerability Scanner
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          severity: 'CRITICAL,HIGH'
          exit-code: '1'
          ignore-unfixed: true

  build-and-push:
    name: Build & Push Container (OIDC)
    needs: [lint-and-test, security-scan]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Build & Push Image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

---

## 2. Core CI/CD Quality Gates

1. **Deterministic Dependency Locking**: Ensure lockfiles (`poetry.lock`, `package-lock.json`, `go.sum`) are committed and strictly verified.
2. **OIDC Authentication**: Eliminate long-lived static API secrets / AWS IAM access keys in CI runners by using GitHub OIDC role assumption.
3. **Pipeline Concurrency**: Cancel stale branch builds when new commits are pushed (`cancel-in-progress: true`).

---

## 3. Matrix Testing & Cache Strategy

```yaml
jobs:
  test:
    strategy:
      fail-fast: false          # one shard failing must not hide the others
      max-parallel: 6
      matrix:
        node: ["20", "22"]
        os: [ubuntu-latest]
        include:
          - node: "22"
            os: ubuntu-latest
            coverage: true      # collect coverage once, not per cell
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node }}
          cache: npm           # keyed on package-lock.json hash
      - run: npm ci            # never `npm install` in CI
      - run: npm test -- --shard=${{ strategy.job-index }}/${{ strategy.job-total }}
```

Cache rules that actually cut minutes:

- Key on a **lockfile hash**, with a prefix-only `restore-keys` fallback; a cache keyed on a
  branch name serves stale dependency trees.
- Cache the package manager's store, not `node_modules`/`vendor` directories.
- Never cache build outputs that feed a release artifact — provenance requires a clean build.

---

## 4. The Same Pipeline in GitLab CI

```yaml
stages: [test, scan, build, deploy]

variables:
  FF_USE_FASTZIP: "true"

.test_template: &test
  stage: test
  cache:
    key:
      files: [package-lock.json]        # lockfile-keyed, same rule as Actions
    paths: [.npm/]
  script: [npm ci --cache .npm --prefer-offline, npm test]

test:node20: { <<: *test, image: node:20 }
test:node22: { <<: *test, image: node:22 }

deploy:prod:
  stage: deploy
  id_tokens:
    AWS_ID_TOKEN: { aud: sts.amazonaws.com }    # OIDC, no static keys
  environment: { name: production, url: https://app.example.com }
  rules: [{ if: '$CI_COMMIT_BRANCH == "main"', when: manual }]
  script:
    - aws sts assume-role-with-web-identity --role-arn "$AWS_ROLE_ARN"
        --web-identity-token "$AWS_ID_TOKEN" --role-session-name gitlab-$CI_JOB_ID
```

The portable pattern across both platforms: lockfile-keyed caches, a job matrix, OIDC for cloud
auth, a manual gate on production, and an environment record so deployments are auditable.
