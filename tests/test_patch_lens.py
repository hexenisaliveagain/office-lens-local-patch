import bz2
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import zipfile
import patch_lens as p


def number(value):
    return (abs(value) | ((1 << 63) if value < 0 else 0)).to_bytes(8, "little")


def delta(tuples, diff, extra, size):
    control = bz2.compress(b"".join(number(n) for row in tuples for n in row))
    differences = bz2.compress(diff)
    return b"BSDIFF40" + number(len(control)) + number(len(differences)) + number(size) + control + differences + bz2.compress(extra)


class PatchTests(unittest.TestCase):
    def test_seek_only_control_tuple(self):
        data = delta([(0, 0, 1), (1, 0, 0)], b"\0", b"", 1)
        self.assertEqual(p.apply_bsdiff(b"ab", data, 1), b"b")

    def test_manifest_rejects_corruption_and_path_escape(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = b"not-the-expected-patch"
            (root / "delta").write_bytes(data)
            manifest = {"schema": 1, "dex": {"patch_file": "delta",
                "patch_sha256": "0" * 64, "target_size": 1}}
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(p.PatchError):
                p.load_manifest(root)
            manifest["dex"]["patch_file"] = "../outside"
            (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaises(p.PatchError):
                p.load_manifest(root)

    def test_add_insert_and_negative_seek(self):
        data = delta([(2, 1, -3), (2, 0, 0)], b"\x01\x00\x07\x01", b"!", 5)
        self.assertEqual(p.apply_bsdiff(b"AB", data, 5), b"BB!\x07B")

    def test_corruption_and_bounds(self):
        valid = delta([(1, 0, 0)], b"\0", b"", 1)
        bad = [b"invalid", valid[:-2], valid + b"junk",
               delta([(2, 0, 0)], b"\0\0", b"", 1),
               delta([(-1, 2, 0)], b"", b"ab", 1),
               delta([(0, 0, 0)], b"", b"", 1),
               delta([(1, 0, 0)], b"", b"", 1)]
        for data in bad:
            with self.subTest(data=data[:32]), self.assertRaises(p.PatchError):
                p.apply_bsdiff(b"a", data, 1)
        with self.assertRaises(p.PatchError):
            p.apply_bsdiff(b"a", valid, 2)

    def test_decompression_limit(self):
        with self.assertRaises(p.PatchError):
            p.decompress_block(bz2.compress(b"x" * 1000), 10)

    def test_no_overwrite_including_fallback(self):
        with tempfile.TemporaryDirectory() as temporary:
            source, target = Path(temporary)/"source", Path(temporary)/"target"
            source.write_bytes(b"new")
            target.write_bytes(b"old")
            for fallback in (False, True):
                with patch.object(p.os, "link", side_effect=OSError() if fallback else FileExistsError()):
                    with self.assertRaises(p.PatchError):
                        p.publish_file(source, target)
                self.assertEqual(target.read_bytes(), b"old")

    def test_payload_and_stored_alignment(self):
        with tempfile.TemporaryDirectory() as temporary:
            old, new = Path(temporary)/"old.zip", Path(temporary)/"new.zip"
            with zipfile.ZipFile(old, "w") as archive:
                archive.writestr("META-INF/OLD.RSA", b"signature")
                archive.writestr("META-INF/services/keep", b"metadata")
                archive.writestr("lib/arm64-v8a/test.so", b"native")
                archive.writestr("żółć.txt", b"unchanged")
                archive.writestr("classes5.dex", b"old")
            with zipfile.ZipFile(old) as archive:
                p.write_unsigned(archive, new, {"classes5.dex": b"new"})
                report = p.verify_payload(archive, new, {"classes5.dex": b"new"})
                self.assertEqual(report["unchanged_payload_entries"], 3)
            raw = new.read_bytes()
            with zipfile.ZipFile(new) as archive:
                self.assertNotIn("META-INF/OLD.RSA", archive.namelist())
                for item in archive.infolist():
                    name_size, extra_size = struct.unpack_from("<HH", raw, item.header_offset + 26)
                    offset = item.header_offset + 30 + name_size + extra_size
                    self.assertEqual(offset % (16384 if item.filename.endswith(".so") else 4), 0)


if __name__ == "__main__":
    unittest.main()
