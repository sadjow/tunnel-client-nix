import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("update", ROOT / "scripts/update.py")
update = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(update)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.platforms = {"test-system": {"asset": "linux-arm64"}}
        self.variants = {"tunnel-client": {}}
        self.asset = "tunnel-client-v0.0.14-linux-arm64.zip"
        self.release = {
            "tag_name": "v0.0.14",
            "assets": [{"name": self.asset}],
            "prerelease": False,
            "draft": False,
        }
        self.checksums = "ab" * 32 + "  " + self.asset + "\n"

    def manifest(self):
        return update.checksum_manifest(self.release, self.checksums, self.platforms, self.variants)

    def test_published_checksum_becomes_nix_hash(self):
        self.assertEqual(self.manifest(), {
            "version": "0.0.14",
            "hashes": {"tunnel-client": {"linux-arm64": "sha256-q6urq6urq6urq6urq6urq6urq6urq6urq6urq6urq6s="}},
        })

    def test_incomplete_release_is_rejected(self):
        self.platforms["second-system"] = {"asset": "darwin-amd64"}
        with self.assertRaisesRegex(ValueError, "darwin-amd64"):
            self.manifest()

    def test_duplicate_checksums_are_rejected(self):
        self.checksums *= 2
        with self.assertRaisesRegex(ValueError, "one published asset and checksum"):
            self.manifest()

    def test_draft_and_prerelease_are_rejected(self):
        for field in ("draft", "prerelease"):
            with self.subTest(field=field):
                self.release[field] = True
                with self.assertRaisesRegex(ValueError, "published stable release"):
                    self.manifest()
                self.release[field] = False

    def test_version_validation_prevents_paths_and_shell_input(self):
        for version in ("../main", "0.0.14;echo hi", "0.0.14-dev", "01.0.0"):
            with self.subTest(version=version), self.assertRaises(ValueError):
                update.release_version(version)
        self.assertEqual(update.release_version("v0.0.14"), "0.0.14")


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "release.json"
        self.original = b'{"version":"0.0.13"}\n'
        self.path.write_bytes(self.original)
        self.desired = {"version": "0.0.14", "hashes": {}}

    @staticmethod
    def fail(*_args):
        raise RuntimeError("verification failed")

    def test_failed_download_never_changes_manifest(self):
        with self.assertRaises(RuntimeError):
            update.apply_update(self.path, self.desired, self.fail, lambda: self.fail())
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_failed_build_restores_exact_previous_bytes(self):
        with self.assertRaises(RuntimeError):
            update.apply_update(self.path, self.desired, lambda _: None, self.fail)
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_successful_update_is_visible_to_build(self):
        def build():
            self.assertEqual(json.loads(self.path.read_text()), self.desired)

        update.apply_update(self.path, self.desired, lambda _: None, build)
        self.assertEqual(json.loads(self.path.read_text()), self.desired)

    def test_failed_first_build_removes_new_manifest(self):
        self.path.unlink()
        with self.assertRaises(RuntimeError):
            update.apply_update(self.path, self.desired, lambda _: None, self.fail)
        self.assertFalse(self.path.exists())
