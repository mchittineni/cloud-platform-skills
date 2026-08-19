# Software Supply Chain Security: SLSA, Sigstore, and Attestation

!!! info "Skill metadata"
    **Name** `supply-chain-security-slsa-sigstore` · **Level** `senior` · **Tags** `supply-chain` `sigstore` `cosign` `slsa` `provenance` `sbom-attestation` `devsecops`

    "Software supply chain security: keyless Sigstore/cosign signing with OIDC, SLSA build levels, in-toto provenance attestations, SBOM attestation, and signature plus identity verification enforced at Kubernetes admission with Kyverno or the sigstore policy-controller. Use when release artifacts or container images need signing, provenance or attestation, when a customer or auditor asks which SLSA level a build meets, or when only trusted and verified images should be allowed to run in a cluster."

    Source: [`skills/02-devsecops-and-secops/supply-chain-security-slsa-sigstore/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/02-devsecops-and-secops/supply-chain-security-slsa-sigstore/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- Container images or release artifacts must be signed, and consumers must verify them
- A customer, auditor, or internal standard asks what SLSA level the build pipeline meets
- Only images with verified provenance should be admitted to a cluster
- An SBOM exists but nothing proves it describes the artifact actually deployed

**Route elsewhere when:**

- Choosing and tuning scanners, or generating the SBOM itself -> `shift-left-security-sast-sca`
- General pipeline structure, caching, OIDC cloud auth -> `cicd-pipeline-design`
- Runtime detection after a workload is already running -> `container-runtime-security-falco`
- Cluster-wide policy authoring beyond image verification -> `policy-as-code-opa-kyverno`

## 1. Sign in CI with keyless OIDC — never a long-lived key

Keyless signing exchanges the workflow's OIDC token for a short-lived Fulcio certificate. There is
no private key to store, rotate, or leak.

```yaml
# .github/workflows/release.yml
permissions:
  contents: read
  packages: write
  id-token: write # REQUIRED: without it, keyless signing cannot mint an OIDC token
  attestations: write

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5

      - name: Build and push by digest
        id: build
        uses: docker/build-push-action@v6
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}

      - uses: sigstore/cosign-installer@v3

      # Sign the DIGEST, never the tag. A tag is a mutable pointer: signing
      # `:v1.4.0` signs whatever that tag meant at signing time, and an attacker
      # who can move the tag inherits a valid signature.
      - name: Sign the image
        env:
          DIGEST: ${{ steps.build.outputs.digest }}
        run: cosign sign --yes "ghcr.io/${{ github.repository }}@${DIGEST}"

      # SLSA provenance: what built this, from which source, with which inputs.
      - name: Attest build provenance
        uses: actions/attest-build-provenance@v2
        with:
          subject-name: ghcr.io/${{ github.repository }}
          subject-digest: ${{ steps.build.outputs.digest }}
          push-to-registry: true

      # Bind the SBOM to the artifact. An unattested SBOM is an unsigned claim.
      - name: Attest the SBOM
        env:
          DIGEST: ${{ steps.build.outputs.digest }}
        run: |
          cosign attest --yes --type cyclonedx \
            --predicate sbom.cdx.json \
            "ghcr.io/${{ github.repository }}@${DIGEST}"
```

## 2. Verification must pin identity, not just check a signature

This is the single most common way image verification is deployed and provides no security at all:

```bash
# WRONG — passes for ANY certificate Fulcio ever issued, to anyone.
cosign verify ghcr.io/acme/api@sha256:abc...

# CORRECT — the signature must come from THIS workflow, via THIS issuer.
cosign verify \
  --certificate-identity-regexp '^https://github\.com/acme/api/\.github/workflows/release\.yml@refs/tags/v.*$' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/acme/api@sha256:abc...

# Verify provenance and read what it claims about the build
gh attestation verify oci://ghcr.io/acme/api@sha256:abc... --repo acme/api
cosign verify-attestation --type cyclonedx \
  --certificate-identity-regexp '^https://github\.com/acme/api/.*$' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/acme/api@sha256:abc...
```

`cosign verify` with no identity flags answers "is this signed by someone?" — which is always yes
for a public transparency log. The security property comes from pinning **who** signed and **which
issuer** attested their identity.

## 3. Enforce at admission, so an unverified image cannot run

Verification in CI is advisory: it proves nothing about what a cluster actually pulls. Enforce at
the admission boundary.

```yaml
# Kyverno: verify signature + identity, and mutate to digest so the check cannot be bypassed
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: verify-image-provenance
spec:
  validationFailureAction: Enforce # Audit first, Enforce once the signal is clean
  webhookTimeoutSeconds: 30
  rules:
    - name: verify-signature
      match:
        any:
          - resources:
              kinds: [Pod]
              namespaces: [production, staging]
      verifyImages:
        - imageReferences: ["ghcr.io/acme/*"]
          mutateDigest: true # rewrite tag -> digest in the admitted spec
          required: true
          attestors:
            - entries:
                - keyless:
                    subject: "https://github.com/acme/*/.github/workflows/release.yml@refs/tags/*"
                    issuer: "https://token.actions.githubusercontent.com"
```

`mutateDigest: true` matters: without it a verified tag can be repointed at an unsigned image
between admission and pull.

## 4. SLSA levels — what each one actually buys

| Level | Requirement | Attack it stops | Typical cost |
| --- | --- | --- | --- |
| L1 | Provenance exists and is available | Nothing on its own; makes builds auditable | Hours |
| L2 | Hosted build service, signed provenance | Forged provenance from a developer laptop | Days |
| L3 | Hardened builder, non-falsifiable provenance, isolated builds | A compromised build step forging its own provenance | Weeks |

GitHub-hosted runners with `actions/attest-build-provenance` reach **L3** for the provenance
property, because the signing identity is minted by the platform and is not reachable from job
steps. Self-hosted runners generally do not: a job that shares a runner with another job can reach
its credentials.

Claim the level the pipeline actually meets. "SLSA L3" on a self-hosted runner with a shared
Docker socket is a false claim an auditor will find.

## 5. Best practices and anti-patterns

**Do:**

- **Sign and reference by digest everywhere** — in CI, in manifests, in Helm values.
- **Start in `Audit` mode**, measure which workloads would fail, then flip to `Enforce`. Enforcing
  first takes production down for images that were fine.
- **Pin third-party GitHub Actions to a commit SHA** and verify the SHA resolves to the tag its
  comment claims. A pin comment naming a version the SHA does not match is worse than no comment.
- **Keep a break-glass path** — a documented, time-boxed, logged policy exception with an owner and
  an expiry date, so an incident is not the moment someone discovers how to bypass admission.
- **Verify base images too.** Signing your layer while pulling an unverified base secures the wrong
  half of the artifact.

**Do not:**

- **Sign a tag.** Mutable reference, worthless signature.
- **Run `cosign verify` without `--certificate-identity*` and `--certificate-oidc-issuer`.** It
  reads as verification in a pipeline log and enforces nothing.
- **Treat an SBOM as evidence.** An SBOM not bound by an attestation to a digest is an unsigned
  text file; anyone can produce a clean one.
- **Store a cosign private key in CI secrets** when keyless works. A stored key is a key that leaks,
  and it cannot be revoked without re-signing every artifact.
- **Enforce policy only in the cluster.** Also block at merge, so failures surface in review rather
  than at 03:00 during a rollout.
- **Skip the revocation story.** Decide in advance how a bad-but-signed artifact is blocked — an
  explicit deny list keyed by digest, plus a tested rebuild-and-resign path.
