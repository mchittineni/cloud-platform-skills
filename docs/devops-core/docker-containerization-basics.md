# Docker Multi-Stage Optimization & Container Hardening

!!! info "Skill metadata"
    **Name** `docker-containerization-basics` · **Level** `junior` · **Tags** `docker` `containers` `multi-stage` `security` `devops-core`

    "Container image engineering: multi-stage builds, layer-cache ordering, non-root users, distroless and minimal base images, and image-size/attack-surface reduction. Use when writing or reviewing a Dockerfile, shrinking image size, fixing slow builds, or hardening containers before they reach a registry."

    Source: [`skills/devops-core/junior-foundation/docker-containerization-basics/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/devops-core/junior-foundation/docker-containerization-basics/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- You are authoring or reviewing a Dockerfile for a production service
- Image size, build time, or layer-cache behaviour needs to improve
- A container must be hardened (non-root, read-only rootfs, minimal base) before release

**Route elsewhere when:**

- Runtime threat detection on a running container -> `container-runtime-security-falco`
- Image CVE scanning and SBOM generation in CI -> `shift-left-security-sast-sca`
- Packaging the image for cluster deployment -> `helm-kubernetes-deployment`

## 1. Production Multi-Stage Dockerfile Pattern

```dockerfile
# syntax=docker/dockerfile:1.4
# Stage 1: Build stage with full compiler toolchain
FROM golang:1.22-alpine AS builder

WORKDIR /app
RUN apk add --no-cache git ca-certificates

# Cache dependencies layer
COPY go.mod go.sum ./
RUN go mod download

# Copy source code and compile statically linked binary
COPY . .
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-w -s" \
    -o /bin/server ./cmd/server

# Stage 2: Minimal non-root runtime image
FROM gcr.io/distroless/static-debian12:nonroot

WORKDIR /
COPY --from=builder /bin/server /server
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/

USER nonroot:nonroot
EXPOSE 8080

ENTRYPOINT ["/server"]
```

---

## 2. Docker Best Practices

- **Layer Caching**: Place commands that change rarely (package installations, dependencies) before code copy commands.
- **Run as Non-Root**: Never run container payloads as `root` (`UID 0`) unless explicitly required by low-level system daemons.
- **Signal Handling**: Ensure PID 1 handles `SIGTERM` and `SIGINT` properly.
- **Scan Before Push**: Run vulnerability scanners prior to registry push (`trivy image <image-tag>`).
