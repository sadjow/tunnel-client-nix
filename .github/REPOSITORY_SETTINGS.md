# Repository setup

Run `bash scripts/setup-github.sh` from a checkout with repository-admin access. It enables automated PR creation, auto-merge availability, and deletion of merged PR branches. Workflows declare their own least-required permissions; the repository's default token remains read-only.

The update workflow validates its candidate with an explicitly called workflow, so it does not need a personal access token to trigger PR checks. Its merge step runs only after all native builds pass and uses `--match-head-commit` to guard against a changed PR. If `main` advances during validation, it leaves the PR open for the next hourly run. Repository protection rules, if added, still apply and may require adapting how update checks are reported.

## Optional Cachix publishing

Create or select a public cache in [Cachix](https://app.cachix.org), then configure its name and write token:

```sh
gh variable set CACHIX_CACHE --body tunnel-client
gh secret set CACHIX_AUTH_TOKEN
```

The second command prompts for the value without placing it in shell history. Use a token scoped to the chosen cache. Do not commit it, place it in Nix expressions, or print it in build output. GitHub secrets from another repository cannot be read back and copied.

Without `CACHIX_CACHE`, publishing jobs are skipped. With a cache name but no valid write token, publishing fails visibly and tags wait for a successful build/cache run. Pull requests never receive the cache write token.

## Verify automation

```sh
gh workflow run build.yml
gh workflow run update.yml
gh run list
```

Actions checks hourly at minute 17. GitHub may delay scheduled jobs and may disable schedules after extended repository inactivity. The interval is a polling schedule, not a guarantee of release availability within an hour.
