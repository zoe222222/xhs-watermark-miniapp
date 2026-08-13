# GitHub Actions Deployment Design

## Goal

Make backend releases behave like Railway: pushing an approved backend change to
`main` automatically deploys it to the Tencent Cloud server and verifies the
running version.

## Architecture

GitHub Actions is the active side of the connection. It packages `backend/`,
copies the archive to the server over a dedicated SSH key, extracts it into the
existing backend directory, and runs Docker Compose with the pushed commit SHA.
The server never needs to connect to GitHub.

The workflow preserves `backend/deploy/Caddyfile`, because that file contains
server-specific HTTP/HTTPS configuration and is not stored in Git. Deployments
overwrite project files but do not delete server-only files.

## Triggers

- Automatically on pushes to `main` that change `backend/**` or the deployment
  workflow itself.
- Manually through `workflow_dispatch` for recovery and verification.
- One deployment at a time; a newer run cancels an older in-progress run.

## SSH Access

Two independent keys are used:

- The existing local administrator key lets this Mac manage the `ubuntu` user.
- A new Ed25519 deploy key is stored only in the repository Actions secret and
  is restricted to deployment use.

After both keys are installed and local key login is verified, SSH password and
keyboard-interactive authentication are disabled through an sshd drop-in. The
current browser terminal remains open until a fresh key-only SSH connection has
been proven.

## GitHub Secrets

- `TENCENT_HOST`: `124.222.91.245`
- `TENCENT_USER`: `ubuntu`
- `TENCENT_SSH_PRIVATE_KEY`: the dedicated Actions private key

The workflow uses SSH port 22. Host keys are collected with `ssh-keyscan` for
the workflow runner's ephemeral `known_hosts` file.

## Deployment And Verification

The remote deployment extracts the archive into
`/home/ubuntu/xhs-watermark-miniapp/backend`, rebuilds with
`sudo docker compose up -d --build`, and checks the local Caddy endpoint. The
workflow then checks the public `/api/version` endpoint and requires its
`gitCommit` value to match the first 12 characters of the pushed SHA.

Any failed command fails the Actions run. Docker Compose continues running the
previous service if transfer or extraction fails before the rebuild.

## Domain Boundary

GitHub Actions solves deployment speed but not WeChat production networking.
The mini-program must eventually use an ICP-filed HTTPS domain configured as
both a request and download domain. Domain registration, payment, identity
verification, SMS verification, and face verification require the account
owner and are outside unattended automation.

