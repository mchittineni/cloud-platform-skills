# Linux SysAdmin & Production Troubleshooting Guide

!!! info "Skill metadata"
    **Name** `linux-sysadmin-troubleshooting` · **Level** `junior` · **Tags** `linux` `sysadmin` `bash` `networking` `troubleshooting` `devops-core`

    "Linux host troubleshooting with the USE method (Utilization, Saturation, Errors): high load average, memory pressure and OOM kills, disk and inode exhaustion, I/O wait, processes hung in D state, socket and DNS failures. Use when a server or VM is degraded, crawling, or unresponsive and needs live hands-on diagnosis, when writes fail with 'No space left on device' despite free space, or when a stuck process must be traced."

    Source: [`skills/01-devops-core/junior-foundation/linux-sysadmin-troubleshooting/SKILL.md`](https://github.com/mchittineni/cloud-platform-skills/blob/main/skills/01-devops-core/junior-foundation/linux-sysadmin-troubleshooting/SKILL.md)


## When to Use This Skill

**Triggers — load this skill when:**

- A node shows high load, memory pressure, disk-full, or I/O wait and you need a systematic first-pass diagnosis
- You need the exact command sequence (top/ps/strace/vmstat/iostat/ss/dig) for a live incident
- You are teaching or reviewing baseline Linux operational competence

**Route elsewhere when:**

- Container-level or Kubernetes-scheduling symptoms -> `docker-containerization-basics` or `helm-kubernetes-deployment`
- Fleet-wide metric collection and alert rules -> `infrastructure-host-monitoring`
- Suspected compromise rather than performance fault -> `secops-incident-triage-forensics`

## 1. Diagnostic Decision Tree

When diagnosing an unresponsive or degraded Linux node, follow the **USE Method** (Utilization, Saturation, and Errors) systematically across CPU, Memory, Disk I/O, and Network.

```text
                  [High Latency / Alert]
                            |
           +----------------+----------------+
           |                |                |
         [CPU]            [Memory]        [Disk / IO]
       top / htop      free -m / vmstat   iostat -xz 1
       mpstat -P ALL   dmesg | grep oom   df -h / df -i
```

---

## 2. Standard Diagnostic Commands

### CPU & Process Inspection

```bash
# 1. Check load average against core count
uptime
nproc

# 2. Top processes sorted by CPU / Memory
top -b -n 1 | head -n 20
ps aux --sort=-%cpu | head -n 10
ps aux --sort=-%mem | head -n 10

# 3. Trace system calls of a stuck process
strace -p <PID> -f -c
```

### Memory & OOM Diagnostics

```bash
# Detailed memory breakdown
free -h --wide

# Check if kernel OOM-killer terminated processes
dmesg -T | grep -i -E "oom|out of memory|killed process"
journalctl -k --grep="Out of memory" -n 50
```

### Disk & Storage Troubleshooting

```bash
# Check filesystem space and Inode exhaustion
df -h
df -i

# Find top 10 space-consuming directories
du -ahx /var/log 2>/dev/null | sort -rh | head -n 10

# Disk I/O utilization & wait times (%util, await)
iostat -xz 1 5
```

### Networking & Socket State

```bash
# Check listening ports and active sockets
ss -tulpn

# Inspect socket queue backlog
ss -s

# Test connection, latency, and DNS resolution
curl -Iv https://example.internal
dig +trace +short api.service.internal
nc -zv 10.0.1.50 443
```

---

## 3. Best Practices & Anti-Patterns

- **Do**: Always inspect Inodes (`df -i`) if `df -h` shows disk space available but writes fail with `No space left on device`.
- **Do**: Look at CPU `%steal` in virtualized cloud environments (AWS EC2 / GCP Compute Engine) to identify noisy neighbors.
- **Don't**: Never use `kill -9` (`SIGKILL`) immediately; attempt graceful `kill -15` (`SIGTERM`) first to allow socket closures and data flushing.
- **Don't**: Avoid running heavy `find /` commands during peak traffic without `-xdev` to avoid crossing network mounts.
