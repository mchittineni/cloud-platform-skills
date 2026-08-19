# Database Management in DevOps & Zero-Downtime Schema Migrations

!!! info "Skill metadata"
    **Name** `database-devops-lifecycle` · **Level** `senior` · **Tags** `database` `migrations` `flyway` `liquibase` `postgresql` `devops-core`

    "Database DevOps: expand/contract zero-downtime schema migration, migration-as-code with Flyway, Liquibase and Atlas, connection pooling, replication lag, and rollback strategy. Use when adding, renaming or dropping a column on a large Postgres or MySQL table without downtime, running migrations from a deploy pipeline, or diagnosing read replicas lagging behind the primary and serving stale data."

    Source: [`skills/devops-core/database-devops-lifecycle/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/devops-core/database-devops-lifecycle/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A schema change must ship without downtime or a locking table rewrite
- Migrations need to be versioned, reviewed, and executed from a pipeline
- Connection exhaustion or replication lag is degrading a service

**Route elsewhere when:**

- Backup, restore, and point-in-time recovery targets -> `backup-and-disaster-recovery`
- Bulk data movement between platforms -> `aws-cloud-migration-strategies`

## 1. Zero-Downtime Expand/Contract Schema Migration Pattern

When modifying database schemas in high-traffic applications, always use the **Expand/Contract (Parallel Run)** technique:

```text
Phase 1 (Expand)   : Add new column (nullable or default). Deploy app writing to BOTH old and new columns.
Phase 2 (Backfill) : Run background async migration job to backfill legacy rows.
Phase 3 (Contract) : Switch app read/write traffic to new column only. Drop old column safely in next release.
```

---

## 2. Liquibase Declarative Migration Example (`db.changelog-1.0.sql`)

```sql
--liquibase formatted sql

--changeset data-platform:20260819-01-add-user-uuid dbms:postgresql
--preconditions onFail:HALT onError:HALT
--precondition-sql-check expectedResult:0 SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'user_uuid';
ALTER TABLE users ADD COLUMN user_uuid UUID DEFAULT gen_random_uuid();
CREATE INDEX CONCURRENTLY idx_users_user_uuid ON users (user_uuid);
--rollback ALTER TABLE users DROP COLUMN user_uuid;
```

---

## 3. Best Practices & Anti-Patterns

- **Do**: Always use `CREATE INDEX CONCURRENTLY` in PostgreSQL to prevent full table exclusive locks.
- **Do**: Enforce database connection pooling (PgBouncer / RDS Proxy) to prevent pod auto-scalers from saturating DB max connection limits.
- **Don't**: Never execute long-running transactional migrations inside CI/CD deployment locks without strict timeouts.

---

## 4. Flyway Versioned Migrations in CI

Flyway enforces an immutable, checksummed, ordered history — the property that makes database
change reviewable like application code.

```text
db/migration/
├── V2026.03.07.01__add_email_verified_column.sql   # versioned, never edited after merge
├── V2026.03.07.02__backfill_email_verified.sql
└── R__refresh_reporting_views.sql                  # repeatable, runs on checksum change
```

```yaml
- name: Migrate (fails closed on checksum drift)
  run: |
    flyway -url="$JDBC_URL" -user="$DB_USER"       -baselineOnMigrate=false -validateOnMigrate=true       -outOfOrder=false migrate
```

Rules that keep this safe:

- Each versioned script is **additive and forward-only**; a mistake is fixed by a new version,
  never by editing a script that has already run (the checksum guard will reject it).
- Long backfills belong in their own migration, batched, and are rerunnable.
- `flyway info` in the pipeline before `migrate` gives the reviewer the exact pending set.

---

## 5. Declarative Schemas with Atlas

Flyway and Liquibase are **imperative**: you write the change. Atlas is **declarative**: you
write the desired schema and it computes the migration, which suits teams that already treat
infrastructure declaratively.

```hcl
# schema.hcl — desired state
table "users" {
  schema = schema.public
  column "id"    { type = uuid, null = false }
  column "email" { type = varchar(320), null = false }
  index "users_email_idx" { columns = [column.email], unique = true }
}
```

```bash
atlas schema diff --from "postgres://…/prod" --to "file://schema.hcl"   # review the plan
atlas migrate diff add_users_email_idx --env prod                        # generate versioned file
atlas migrate lint --env prod --latest 1                                 # catch destructive changes
```

`atlas migrate lint` is the part worth adopting even alongside Flyway: it flags
backwards-incompatible and table-locking changes in review, before they reach production.
Declarative tooling still needs the expand/contract discipline — it will happily generate a
`DROP COLUMN` that breaks the running version.
