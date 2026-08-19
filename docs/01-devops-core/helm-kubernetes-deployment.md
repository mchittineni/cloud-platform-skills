# Production Helm Chart Engineering & Kubernetes Packaging

!!! info "Skill metadata"
    **Name** `helm-kubernetes-deployment` · **Level** `mid` · **Tags** `helm` `kubernetes` `k8s` `packaging` `devops-core`

    "Helm chart engineering: chart/subchart layout, values schema validation, hardened Deployment templates (probes, resources, securityContext, PDB), and release lifecycle with rollback. Use when authoring or reviewing a Helm chart, templating Kubernetes manifests, or debugging a failed or stuck Helm release."

    Source: [`skills/01-devops-core/mid-level-automation/helm-kubernetes-deployment/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/01-devops-core/mid-level-automation/helm-kubernetes-deployment/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A service needs a production chart with probes, limits, and securityContext set correctly
- Chart values need schema validation or environment layering
- A `helm upgrade` failed, hung, or must be rolled back

**Route elsewhere when:**

- Progressive canary/blue-green rollout control -> `zero-downtime-release-strategies`
- Continuous reconciliation of charts across clusters -> `gitops-multi-cluster-argo-flux`
- Managed-cluster/node-pool design -> `aws-eks-enterprise-patterns`, `azure-aks-enterprise-landing-zones`, `gcp-gke-autopilot-multi-tenant`

## 1. Production Chart Architecture

```text
chart/
├── Chart.yaml
├── values.yaml
├── values.schema.json       # JSON Schema validation for inputs
└── templates/
    ├── _helpers.tpl         # Standardized label macros
    ├── deployment.yaml
    ├── service.yaml
    ├── hpa.yaml
    └── pdb.yaml
```

---

## 2. Hardened Deployment Manifest Template (`deployment.yaml`)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "app.fullname" . }}
  labels:
    {{- include "app.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "app.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "app.selectorLabels" . | nindent 8 }}
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: {{ .Chart.Name }}
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          ports:
            - name: http
              containerPort: {{ .Values.service.port }}
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 15
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

---

## 3. Deployment Safety Rules

- **Pod Disruption Budgets (PDB)**: Always define a `PodDisruptionBudget` for production workloads (`minAvailable: 1` or `maxUnavailable: 25%`).
- **Resource Requests & Limits**: Never omit CPU and memory requests and limits; prevent noisy neighbor starvation.
- **Topology Spread Constraints**: Distribute pods evenly across availability zones to withstand cloud node/zone outages.

---

## 4. Probe Separation & Release Lifecycle

**Three probes, three different questions.** Reusing one endpoint for all three is the most
common cause of restart loops on slow-starting services:

```yaml
startupProbe:            # "has it finished booting?" — buys slow starters time
  httpGet: { path: /healthz, port: http }
  failureThreshold: 30
  periodSeconds: 5       # up to 150s to start; liveness stays disabled until this passes
livenessProbe:           # "is it wedged and in need of a restart?" — cheap, no dependencies
  httpGet: { path: /healthz, port: http }
  periodSeconds: 10
  failureThreshold: 3
readinessProbe:          # "should it receive traffic right now?" — may check dependencies
  httpGet: { path: /readyz, port: http }
  periodSeconds: 5
  failureThreshold: 2
```

A liveness probe that checks the database restarts every replica during a database blip. Keep
dependency checks in readiness only.

### Release lifecycle

```bash
helm upgrade --install api ./chart -f values.prod.yaml   --atomic --timeout 5m --wait          # --atomic auto-rolls back a failed upgrade
helm history api                        # revision, status, chart/app version
helm rollback api 7 --wait              # deterministic return to a known-good revision
helm get values api --revision 7        # what was actually deployed then
```

Stuck in `pending-upgrade` usually means a previous run was killed mid-flight: inspect
`helm history`, then `helm rollback` to the last `deployed` revision rather than deleting the
release secret by hand.
