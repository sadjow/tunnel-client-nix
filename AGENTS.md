# Repository guidance

This repository owns the Nix packaging and release automation. Upstream owns the executables and their runtime behavior.

- Read [maintenance notes](docs/maintenance.md) before changing package layout, platform coverage, or release automation.
- Use `release.json`, `platforms.json`, and `variants.json` as the authoritative release, platform, and variant data. Keep workflows and package expressions derived from them.
- Run `nix flake check`, `nix fmt -- --check *.nix`, and `nix develop --command actionlint` before committing. All four native CI platforms must pass before automated release merging or tagging.
- Keep credentials and generated runtime profiles out of this repository and the Nix store. Tests must not require an OpenAI account or create a tunnel.
