# Platform Engineering: Spotify Backstage & Golden Path Scaffolding

!!! info "Skill metadata"
    **Name** `internal-developer-portal-backstage` · **Level** `staff` · **Tags** `platform-engineering` `backstage` `idp` `golden-paths` `devex`

    "Internal Developer Platform engineering: Backstage software catalog and entity model, Golden Path scaffolder templates, TechDocs, and platform-as-product adoption and DevEx metrics. Use when building self-service so developers can create a new production-ready service in one click, defining golden paths, onboarding services into a catalog, or measuring platform adoption."

    Source: [`skills/platform-engineering/internal-developer-portal-backstage/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/platform-engineering/internal-developer-portal-backstage/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A platform team needs a catalog, scaffolder template, or golden path defined
- Service onboarding and ownership metadata must be standardized
- Platform adoption or DevEx needs to be measured as a product

**Route elsewhere when:**

- Underlying delivery automation -> `cicd-pipeline-design` and `gitops-multi-cluster-argo-flux`
- Delivery performance measurement -> `devops-metrics-dora-kpis`

## 1. Backstage Software Template Definition (`template.yaml`)

```yaml
apiVersion: scaffolder.backstage.io/v1beta3
kind: Template
metadata:
  name: springboot-microservice-template
  title: Production Spring Boot Microservice
  description: Scaffolds a 12-factor Spring Boot service with CI/CD, Helm charts, and OpenTelemetry
spec:
  owner: platform-team
  type: service

  parameters:
    - title: Service Configuration
      required: [component_id, description, owner]
      properties:
        component_id:
          title: Unique Service Name
          type: string
          pattern: '^[a-z0-9-]+$'
        description:
          title: Description
          type: string
        owner:
          title: Owner Team
          type: string
          ui:field: OwnerPicker

  steps:
    - id: fetch-base
      name: Fetch Template Skeleton
      action: fetch:template
      input:
        url: ./skeleton
        values:
          component_id: ${{ parameters.component_id }}
          owner: ${{ parameters.owner }}

    - id: publish-github
      name: Publish Repository to GitHub
      action: publish:github
      input:
        repoUrl: github.com?owner=my-org&repo=${{ parameters.component_id }}
        defaultBranch: main

    - id: register-catalog
      name: Register in Backstage Catalog
      action: catalog:register
      input:
        repoContentsUrl: ${{ steps['publish-github'].output.repoContentsUrl }}
        catalogInfoPath: '/catalog-info.yaml'
```

---

## 2. Platform Engineering Golden Rules

- **Paved Road over Mandates**: Build self-service workflows that make the secure and reliable way the easiest way for product engineers.
- **Treat the Platform as a Product**: Measure internal customer Net Promoter Score (NPS), Time to 10th Deployment, and lead time for changes (DORA).
- **Service Ownership via Catalog**: Require clear team ownership, on-call links, and API specifications for every registered component.

---

## 3. TechDocs as the Documentation Plane

TechDocs renders docs-as-code from each service's own repository into the portal, so
documentation lives beside the code it describes and is reviewed in the same PR:

```yaml
# catalog-info.yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: payments-api
  annotations:
    backstage.io/techdocs-ref: dir:.        # mkdocs.yml at the repo root
    backstage.io/source-location: url:https://github.com/acme/payments-api
spec:
  type: service
  lifecycle: production
  owner: group:payments
  system: checkout
```

```yaml
# mkdocs.yml
site_name: Payments API
nav: [Overview: index.md, Runbook: runbook.md, API: api.md]
plugins: [techdocs-core]
```

Build docs in CI and publish to object storage (the external build pipeline), not on the Backstage
server — in-server builds make the portal slow and couple its uptime to doc rendering. Make the
scaffolder template emit `mkdocs.yml`, an `index.md` and a `runbook.md` stub so every new service
starts with a documentation surface, and treat a missing runbook annotation as a catalog lint
failure rather than a suggestion.

---

## 4. Anti-Patterns

| Anti-pattern | Why it fails in production |
| --- | --- |
| Launching the catalog by bulk-importing every repository | Thousands of entities with stale or absent owners, so the first lookup a developer tries returns garbage and they never come back. Onboard the services people actually page for, with real owners. |
| Mandating platform adoption instead of earning it | Teams comply on paper and keep their own pipelines underneath, so you now maintain two systems. Golden paths must be the fastest route to production, or they are shelfware. |
| A scaffolder template that generates a repository and nothing else | The developer still has to request CI, credentials, infrastructure and on-call registration by hand — the one-click promise breaks at step two. A golden path provisions the whole chain or it is a file generator. |
| Treating the portal as a project with an end date | The catalog rots the moment nobody owns it; six months later ownership data is wrong and the portal is a liability during incidents. Staff it as a product with a roadmap. |
| Measuring adoption by page views | Views measure curiosity. Measure the outcomes the platform exists to change: time from repo creation to first production deploy, share of services on the golden path, and change failure rate for those services. |
| Building the portal before talking to developers | You automate the steps that were easy to automate rather than the ones that hurt. Start from the top three sources of developer friction, evidenced by a survey or by watching an onboarding. |
| Running TechDocs builds on the Backstage server | Doc rendering competes with the portal's own uptime and gets slow as the catalog grows. Build docs in CI and publish to object storage. |
