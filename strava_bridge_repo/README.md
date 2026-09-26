# Strava Bridge

A tiny GitHub-hosted job that keeps pulling your Strava activities on a
schedule, with no laptop or phone needing to be on. Claude reads the result
straight from this repo and pushes it into the Start Line app.

## One-time setup

1. Create a new **private** GitHub repository and upload these files to it
   (keep the `.github/workflows/strava-sync.yml` path exactly as-is).
2. Go to the repo's **Settings → Actions → General → Workflow permissions**
   and select **"Read and write permissions"**, then Save. (This lets the
   workflow commit its own results back to the repo.)
3. Go to **Settings → Secrets and variables → Actions** and add three
   repository secrets:
   - `STRAVA_CLIENT_ID`
   - `STRAVA_CLIENT_SECRET`
   - `STRAVA_REFRESH_TOKEN`
4. Go to the **Actions** tab, open "Strava sync", and click **"Run workflow"**
   once to confirm it runs green. After that it runs automatically every
   20 minutes.
5. Create a **fine-grained personal access token** (Settings, top-right
   avatar → **Developer settings → Personal access tokens → Fine-grained
   tokens → Generate new token**), scoped to **only this repository**, with
   **Contents: Read-only** permission. Send that token back so it can be
   wired into the Claude side.
