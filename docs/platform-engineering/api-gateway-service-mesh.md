# API Gateway & Service Mesh (Istio & Envoy) Architecture

!!! info "Skill metadata"
    **Name** `api-gateway-service-mesh` · **Level** `senior` · **Tags** `api-gateway` `service-mesh` `istio` `envoy` `kong` `platform-engineering`

    "API gateway and service mesh architecture: Istio strict mTLS and authorization policy, VirtualService traffic shifting, Envoy Gateway and Kong ingress, retries/timeouts/outlier detection, and rate limiting. Use when configuring ingress routing, enforcing zero-trust service-to-service traffic, or debugging mesh routing and mTLS failures."

    Source: [`skills/platform-engineering/api-gateway-service-mesh/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/platform-engineering/api-gateway-service-mesh/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- North-south ingress or east-west mesh routing must be designed or changed
- Service-to-service traffic needs mTLS and authorization policy
- A 503/routing/mTLS failure inside the mesh needs diagnosis

**Route elsewhere when:**

- Weighted rollout automation -> `zero-downtime-release-strategies`
- Application-side resilience patterns -> `scalability-high-availability-patterns`
- Mesh telemetry pipelines -> `prometheus-grafana-otel-tracing`

## 1. Istio Zero-Trust Strict mTLS & VirtualService Traffic Shifting

```yaml
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: production
spec:
  mtls:
    mode: STRICT # Enforce encrypted mTLS across all service-to-service traffic
---
apiVersion: networking.istio.io/v1alpha3
kind: VirtualService
metadata:
  name: user-service-route
  namespace: production
spec:
  hosts:
    - "user-service.production.svc.cluster.local"
  http:
    - route:
        - destination:
            host: user-service.production.svc.cluster.local
            subset: v1
          weight: 90
        - destination:
            host: user-service.production.svc.cluster.local
            subset: v2
          weight: 10
      retries:
        attempts: 3
        perTryTimeout: 2s
        retryOn: "5xx,connect-failure,refused-stream"
```

---

## 2. Best Practices & Anti-Patterns

- **Do**: Enforce `STRICT` mTLS across internal namespaces to prevent unauthenticated lateral movement.
- **Do**: Implement API Gateway rate limiting and authentication (JWT verification) at the edge before traffic enters the cluster mesh.
- **Don't**: Never configure retries without idempotent request semantics or backoff limits.

---

## 3. Default-Deny Authorization & Outlier Detection

mTLS proves _who_ is calling; authorization decides _whether they may_. Strict mTLS without an
AuthorizationPolicy still allows every service to call every other service.

```yaml
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata: { name: deny-all, namespace: prod }      # 1. default deny for the namespace
spec: {}                                            # empty spec + no rules = deny everything
---
apiVersion: security.istio.io/v1
kind: AuthorizationPolicy
metadata: { name: checkout-allow-from-web, namespace: prod }
spec:
  selector: { matchLabels: { app: checkout } }
  action: ALLOW
  rules:
    - from:
        - source:
            principals: ["cluster.local/ns/prod/sa/web-frontend"]   # SPIFFE identity, not IP
      to:
        - operation: { methods: ["POST"], paths: ["/api/v1/checkout"] }
```

**DestinationRule** carries the client-side resilience settings the application would otherwise
have to implement:

```yaml
apiVersion: networking.istio.io/v1
kind: DestinationRule
metadata: { name: checkout, namespace: prod }
spec:
  host: checkout.prod.svc.cluster.local
  trafficPolicy:
    tls: { mode: ISTIO_MUTUAL }
    connectionPool:
      tcp: { maxConnections: 200, connectTimeout: 2s }
      http: { http2MaxRequests: 500, maxRequestsPerConnection: 100 }
    outlierDetection:                 # passive health checking = circuit breaking
      consecutive5xxErrors: 5
      interval: 10s
      baseEjectionTime: 30s
      maxEjectionPercent: 50          # never eject the whole fleet
  subsets:
    - name: v1
      labels: { version: v1 }
    - name: v2
      labels: { version: v2 }
```

`503 UC`/`UF` means the sidecar could not reach upstream: check `istioctl proxy-config
endpoints`, whether the port name carries the right protocol prefix, and whether outlier
detection has ejected the endpoints. `maxRequestsPerConnection: 1` disables keep-alive — set it
only for upstreams that mishandle connection reuse.

---

## 4. Gateway Choice: Istio Gateway, Envoy Gateway or Kong

North-south ingress and east-west mesh are separate decisions; conflating them produces two
overlapping control planes.

| Option | Config surface | Choose it when |
| --- | --- | --- |
| Istio Ingress Gateway | Istio CRDs (`Gateway`, `VirtualService`) | The mesh is already Istio and one control plane is preferred |
| Envoy Gateway | Kubernetes Gateway API (`HTTPRoute`, `GRPCRoute`) | Standards-based routing wanted, mesh-agnostic, no Istio lock-in |
| Kong | Kong CRDs / declarative config, plugin ecosystem | API-management needs dominate: consumers, keys, quotas, monetisation |

```yaml
# Gateway API — portable across Envoy Gateway, Istio and Kong implementations
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata: { name: checkout, namespace: prod }
spec:
  parentRefs: [{ name: public-gateway, namespace: istio-system }]
  hostnames: ["checkout.example.com"]
  rules:
    - matches: [{ path: { type: PathPrefix, value: /api/v1 } }]
      timeouts: { request: 10s }
      backendRefs: [{ name: checkout, port: 8080, weight: 100 }]
```

Prefer Gateway API for new ingress: it is the direction all three implementations are moving, and
it keeps the routing contract portable while mesh-internal policy stays in Istio CRDs. Kong earns
its place when the requirement is an API product (consumer onboarding, rate-limit tiers, keys),
not merely routing.
