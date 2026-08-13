# GitHub Actions Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically deploy backend changes from GitHub to Tencent Cloud without requiring the server to access GitHub.

**Architecture:** A native OpenSSH GitHub Actions workflow sends a backend archive to the existing server, rebuilds Docker Compose, and verifies the deployed commit. Dedicated SSH credentials isolate automation from administrator access.

**Tech Stack:** GitHub Actions, OpenSSH, tar, Docker Compose, Python unittest

**Spec:** `docs/superpowers/specs/2026-08-14-github-actions-deployment-design.md`

## Global Constraints

- Preserve the server-only `backend/deploy/Caddyfile`.
- Do not require the Tencent Cloud server to connect to GitHub.
- Disable password authentication only after fresh key-only login succeeds.
- Run the repository pre-release check before pushing.

---

### Task 1: Deployment Workflow Contract

**Files:**
- Create: `tests/test_deploy_workflow.py`
- Create: `.github/workflows/deploy-backend.yml`

**Interfaces:**
- Consumes: repository `backend/` directory and three GitHub Actions secrets.
- Produces: automatic deployment on backend changes and manual deployment through `workflow_dispatch`.

- [ ] **Step 1: Write the failing workflow contract test**

Assert that the workflow is absent or lacks the required triggers, secret names,
archive transfer, Caddyfile preservation, Docker rebuild, and version check.

- [ ] **Step 2: Run the test to verify it fails**

Run: `python3 -m unittest tests.test_deploy_workflow -v`
Expected: FAIL because `.github/workflows/deploy-backend.yml` does not exist.

- [ ] **Step 3: Create the minimal workflow**

Use `actions/checkout`, native `ssh`, `scp`, and `tar`; deploy only backend
content, preserve the Caddyfile, rebuild Docker, and compare `/api/version`
against `${GITHUB_SHA::12}`.

- [ ] **Step 4: Run the test to verify it passes**

Run: `python3 -m unittest tests.test_deploy_workflow -v`
Expected: PASS.

### Task 2: SSH Key-Only Access

**Files:**
- Server: `/home/ubuntu/.ssh/authorized_keys`
- Server: `/etc/ssh/sshd_config.d/99-key-only.conf`

**Interfaces:**
- Consumes: local administrator public key and dedicated Actions public key.
- Produces: key-only SSH access for `ubuntu` on port 22.

- [ ] **Step 1: Generate the dedicated Ed25519 Actions key**
- [ ] **Step 2: Install both public keys with strict permissions**
- [ ] **Step 3: Verify fresh administrator key login from this Mac**
- [ ] **Step 4: Validate sshd configuration before reloading it**
- [ ] **Step 5: Disable password and keyboard-interactive authentication**
- [ ] **Step 6: Verify another fresh key-only login after reload**

### Task 3: GitHub Integration And Live Deployment

**Files:**
- GitHub repository Actions secrets

**Interfaces:**
- Consumes: dedicated private key, server host, and server user.
- Produces: a successful live deployment run whose public version matches Git.

- [ ] **Step 1: Add the three repository Actions secrets**
- [ ] **Step 2: Run all repository tests and `/pre-release-check`**
- [ ] **Step 3: Commit only deployment-owned files and push `main`**
- [ ] **Step 4: Observe the Actions run to completion**
- [ ] **Step 5: Verify public `/api/version` and the original xhslink.cn request**

