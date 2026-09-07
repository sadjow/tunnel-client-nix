# Maintenance notes

## Ownership and source lineage

This is an independently maintained packaging repository owned by Sadjow. Its initial feature set was adapted from:

- `sadjow/claude-code-nix` at `806752b6b51c5a3f9362fd60aed838c891b5c58b`: native binaries, flake outputs, hourly updates, Cachix, pinned Actions, and version tags.
- `sadjow/codex-cli-nix` at `3a0dca3725f6d8b74cfe635a85724d2313731fb4`: multiple variants, companion placement, shell completions, and installation examples.
- `openai/tunnel-client` release `v0.0.14`, source commit `0f870e50a973fa820d4c409000059e181e8d242b`: archive contents, CLI behavior, and companion discovery.

These are provenance references, not runtime dependencies. Changes flow here through deliberate review; this repo does not automatically rewrite or synchronize the other packaging projects.

## Release payload

The full client and cloudflared runtime resolve their companion beside the actual executable. Preserve that relationship under each variant's `libexec` directory. A global cloudflared symlink is unnecessary and would collide when multiple variants are installed together. The plain runtime has no companion.

Upstream runtime variants explicitly disable Cobra's completion command. Only generate completions for variants that expose it. Preserve signed macOS executables and embedded Go metadata by disabling stripping and ELF patching. If a later Linux release becomes dynamically linked, inspect the actual binary and adapt the packaging before claiming it works on NixOS.

The install checks cover the original full-client/companion relationship, transfer to the cloudflared runtime, and the plain-runtime boundary. Native CI covers all declared systems, rather than assuming the platform list implies tested support.

## Platform lifecycle

The unstable Nixpkgs snapshot used by the reference repos rejected `x86_64-darwin` during initial evaluation with the explicit message that Nixpkgs 26.11 dropped support. Use the maintained 26.05 Darwin input for that system. Other platforms continue using unstable; overlay consumers retain control of their own package sets.

Reassess the Intel input as its upstream maintenance ends. Do not remove an existing platform merely to make a lock update pass. Distinguish upstream support policy from observed package compatibility and discuss any loss of coverage.

## Automation invariants

- Obtain the complete desired release manifest before modifying it. Verify downloads against the upstream checksum file. Missing assets or ambiguous checksums fail the update.
- A version match alone is insufficient: missing or drifted hashes still need reconciliation.
- Treat discovery errors as failures, not as available updates or successful no-ops.
- Validate the candidate's exact commit before merging. The bot invokes the reusable matrix explicitly because `GITHUB_TOKEN` PR creation does not trigger normal PR workflows.
- Guard both the PR head and the observed main base. If either moves, leave the update for a new validation run.
- Main publication checks the tested SHA against current main. Immutable version tags stay fixed; only the documented moving tags are replaced.
- Cache writes happen only on main after validation. Candidate and fork builds receive no cache write credentials.

The portable principles are already covered by the maintainer's cross-project instructions on reconciliation, tested support, and failure propagation. The concrete findings and executable checks remain project-owned; no personal-machine paths are required.
