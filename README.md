# tunnel-client-nix

Nix packages for [OpenAI Secure MCP Tunnel](https://github.com/openai/tunnel-client), with hourly stable-release checks and native builds on Linux and macOS.

## Features

- Official release binaries, pinned by SHA-256 and checked against upstream checksums.
- Full client and both smaller runtime variants.
- Native CI for Apple Silicon, Intel macOS, ARM64 Linux, and x86_64 Linux.
- Hourly update PRs, merged only after all four platforms pass.
- Optional Cachix publishing after validation.
- Immutable release tags, moving `latest` and major-version tags, and flake-lock pinning.
- Flake packages, apps, an overlay, a development shell, and Bash/Fish/Zsh completions for the full client.

## Quick start

Enable the `nix-command` and `flakes` experimental features in your Nix installation, then run:

```sh
nix run github:sadjow/tunnel-client-nix -- --version
nix run github:sadjow/tunnel-client-nix -- help quickstart
```

Install into a standalone profile:

```sh
nix profile add github:sadjow/tunnel-client-nix
tunnel-client --version
```

Older Nix releases call the profile command `nix profile install`.

```sh
nix profile upgrade --all
nix profile rollback
```

The package does not create a tunnel or start a service. Follow the client's `help quickstart` and [upstream onboarding guide](https://github.com/openai/tunnel-client/blob/master/docs/onboarding.md) to configure your connection.

## Package variants

| Output | Executable | Included capabilities |
| --- | --- | --- |
| `default`, `tunnel-client` | `tunnel-client` | Full CLI, admin UI, setup helpers, bundled cloudflared |
| `tunnel-client-runtime` | `tunnel-client-runtime` | Smaller tunnel runtime |
| `tunnel-client-runtime-cloudflared` | `tunnel-client-runtime-cloudflared` | Smaller runtime with bundled cloudflared |

```sh
nix run github:sadjow/tunnel-client-nix#tunnel-client-runtime -- --help
nix run github:sadjow/tunnel-client-nix#tunnel-client-runtime-cloudflared -- --help
```

The companion stays beside its associated executable under `libexec`. It is not added to your global PATH. Upstream licenses, notices, dependency license reports, and SBOMs are preserved under `share/doc/<variant>`.

## Home Manager, NixOS, and nix-darwin

Add the input to your flake:

```nix
inputs.tunnel-client-nix.url = "github:sadjow/tunnel-client-nix";
```

Then add the package to Home Manager:

```nix
{ inputs, pkgs, ... }:
{
  home.packages = [
    inputs.tunnel-client-nix.packages.${pkgs.stdenv.hostPlatform.system}.default
  ];
}
```

For NixOS or nix-darwin, use the same package in `environment.systemPackages`. Pass `inputs` through your configuration's `specialArgs` or `extraSpecialArgs` when using these examples.

The overlay is also available:

```nix
nixpkgs.overlays = [ inputs.tunnel-client-nix.overlays.default ];
home.packages = [ pkgs.tunnel-client ];
```

Keep API keys in runtime environment variables or files outside the Nix store. This repository packages executables; service configuration remains owned by your system or Home Manager configuration.

## Platforms and version pinning

The flake provides `aarch64-darwin`, `x86_64-darwin`, `aarch64-linux`, and `x86_64-linux`. Native CI builds and smoke-tests every variant on each platform.

Intel macOS uses `nixpkgs-26.05-darwin`, because Nixpkgs 26.11 removed that platform. The other platforms use `nixpkgs-unstable`. Both inputs are locked. The overlay uses the consuming configuration's package set.

For an exact upstream release:

```nix
inputs.tunnel-client-nix.url = "github:sadjow/tunnel-client-nix/v0.0.14";
```

Use a commit SHA when you also need to pin packaging revisions. Release tags remain immutable; `latest` and `v0` move to successfully validated main commits. A consumer's `flake.lock` pins even a moving reference until explicitly updated:

```sh
nix flake update tunnel-client-nix
```

## Binary cache

The public cache is [tunnel-client.cachix.org](https://tunnel-client.cachix.org). Enable it with:

```sh
cachix use tunnel-client
```

For declarative NixOS or nix-darwin configuration:

```nix
nix.settings = {
  extra-substituters = [ "https://tunnel-client.cachix.org" ];
  extra-trusted-public-keys = [
    "tunnel-client.cachix.org-1:m5ve4z3WgkbTn0GwDRbBCG76dJBlTjv9TR93sO3AaqA="
  ];
};
```

CI publishing requires the `CACHIX_CACHE` repository variable and the `CACHIX_AUTH_TOKEN` secret. Without a cached output, packages build directly from upstream archives; no Go compilation is required. Cache publishing is limited to validated main commits. See [repository setup](.github/REPOSITORY_SETTINGS.md) for enabling publishing.

## Development and updates

```sh
nix develop
python3 scripts/update.py --check
python3 scripts/update.py
python3 scripts/update.py --version 0.0.14
nix flake check --print-build-logs
nix fmt -- --check *.nix
actionlint
```

`--check` prints JSON containing `current`, `latest`, and `update_needed`, and succeeds when the check itself succeeds. API and checksum errors return a failure status. The updater compares the entire desired manifest, so it also repairs missing or incorrect hashes for an unchanged version.

An update downloads and verifies every platform archive before replacing `release.json`. The normal command runs local flake checks and restores the previous manifest if a build fails. `--no-build` explicitly defers build validation to another step. Updating package releases does not change the Nixpkgs lock; use `nix flake update` and validate all platforms when refreshing dependencies.

The hourly workflow creates or refreshes one update PR, validates its exact commit through a reusable four-platform workflow, checks that its base has not changed, and merges using a head-commit guard. It explicitly dispatches the main build afterward because pushes made with `GITHUB_TOKEN` do not trigger normal push workflows. Main builds validate, optionally publish to Cachix, then publish tags for the tested commit.

The unit tests cover incomplete releases, ambiguous checksums, version validation, and atomic update recovery. Build checks execute `--version` and `--help`, generate the full client's completions, and run each bundled companion's version command. They do not authenticate to OpenAI or establish a live tunnel.

## License and provenance

The packaging is MIT-licensed. OpenAI tunnel-client is Apache-2.0-licensed; bundled dependencies retain their own licenses.

See [maintenance notes](docs/maintenance.md) for the source revisions used to establish this repository and the packaging invariants.
