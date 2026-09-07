#!/usr/bin/env python3
"""Refresh the complete release manifest after verifying every archive."""

import argparse
import base64
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
REPOSITORY = "openai/tunnel-client"


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def release_version(value):
    version = value.removeprefix("v")
    if not re.fullmatch(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)", version):
        raise ValueError("Expected a stable release version such as 0.0.14")
    return version


def checksum_manifest(release, checksums, platforms, variants):
    if release.get("draft") or release.get("prerelease"):
        raise ValueError("Automatic packaging requires a published stable release")
    version = release_version(release["tag_name"])
    assets = {asset["name"] for asset in release["assets"]}
    entries = {}
    for line in checksums.splitlines():
        match = re.fullmatch(r"([0-9a-fA-F]{64}) [ *](.+)", line)
        if match:
            digest, name = match.groups()
            entries.setdefault(name, []).append(digest)

    hashes = {}
    for variant in variants:
        hashes[variant] = {}
        for platform in platforms.values():
            asset = platform["asset"]
            name = f"{variant}-v{version}-{asset}.zip"
            if name not in assets or len(entries.get(name, [])) != 1:
                raise ValueError(f"Expected one published asset and checksum for {name}")
            digest = bytes.fromhex(entries[name][0])
            hashes[variant][asset] = "sha256-" + base64.b64encode(digest).decode()
    return {"version": version, "hashes": hashes}


def verify_archives(manifest):
    version = manifest["version"]
    for variant, platforms in manifest["hashes"].items():
        for platform, expected_hash in platforms.items():
            name = f"{variant}-v{version}-{platform}.zip"
            url = f"https://github.com/{REPOSITORY}/releases/download/v{version}/{name}"
            print(f"Verifying {name}", file=sys.stderr)
            result = json.loads(run(
                "nix", "store", "prefetch-file", "--json",
                "--hash-type", "sha256", "--expected-hash", expected_hash, url,
            ))
            if result["hash"] != expected_hash:
                raise ValueError(f"Archive checksum mismatch: {name}")


def atomic_write(path, data):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temporary:
        temporary.write(data)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.chmod(0o644)
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def apply_update(path, manifest, verify, build):
    previous = path.read_bytes() if path.exists() else None
    verify(manifest)
    atomic_write(path, (json.dumps(manifest, indent=2) + "\n").encode())
    try:
        build()
    except BaseException:
        if previous is None:
            path.unlink(missing_ok=True)
        else:
            atomic_write(path, previous)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", type=release_version)
    parser.add_argument("--check", action="store_true", help="Print JSON status without changing files")
    parser.add_argument("--no-build", action="store_true", help="Defer builds to the CI platform matrix")
    args = parser.parse_args()
    endpoint = f"tags/v{args.version}" if args.version else "latest"
    release = json.loads(run("gh", "api", f"repos/{REPOSITORY}/releases/{endpoint}"))
    if args.version and release_version(release["tag_name"]) != args.version:
        raise ValueError("Release API returned a different version")
    with tempfile.TemporaryDirectory(prefix="tunnel-client-checksums-") as directory:
        subprocess.run([
            "gh", "release", "download", release["tag_name"], "--repo", REPOSITORY,
            "--pattern", "SHA256SUMS.txt", "--dir", directory,
        ], check=True)
        checksums = (Path(directory) / "SHA256SUMS.txt").read_text()

    platforms = json.loads((ROOT / "platforms.json").read_text())
    variants = json.loads((ROOT / "variants.json").read_text())
    desired = checksum_manifest(release, checksums, platforms, variants)
    path = ROOT / "release.json"
    current = json.loads(path.read_text()) if path.exists() else {}
    status = {
        "current": current.get("version"),
        "latest": desired["version"],
        "update_needed": current != desired,
    }
    if args.check:
        print(json.dumps(status))
        return
    if status["update_needed"]:
        def build():
            if not args.no_build:
                subprocess.run(["nix", "flake", "check", f"path:{ROOT}", "--print-build-logs"], check=True)

        apply_update(path, desired, verify_archives, build)
    print(json.dumps(status))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Update failed: {error}", file=sys.stderr)
        sys.exit(1)
