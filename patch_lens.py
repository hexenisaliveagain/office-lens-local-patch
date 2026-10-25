#!/usr/bin/env python3
"""Version-bound, offline Microsoft Lens patcher. Python standard library only."""
from __future__ import annotations

import argparse
import bz2
import copy
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

VERSION = "1.0.0"
ROOT = Path(__file__).resolve().parent
MAX_DEX_SIZE = 32 * 1024 * 1024
MAX_CONTROL_SIZE = 8 * 1024 * 1024
SIGNATURE_ENTRY = re.compile(r"META-INF/[^/]+\.(?:SF|RSA|DSA|EC|MF)", re.IGNORECASE)


class PatchError(Exception):
    """Input, patch, or build verification failed."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def require_hash(data: bytes, expected: str, label: str) -> None:
    actual = sha256(data)
    if actual != expected:
        raise PatchError(f"{label}: SHA-256 mismatch. Expected {expected}; got {actual}.")


def read_offset(data: bytes, offset: int) -> int:
    """BSDIFF40 uses little-endian signed magnitude, not two's complement."""
    if offset < 0 or offset + 8 > len(data):
        raise PatchError("Truncated BSDIFF40 integer.")
    value = int.from_bytes(data[offset:offset + 8], "little")
    magnitude = value & ((1 << 63) - 1)
    return -magnitude if value >> 63 else magnitude


def decompress_block(data: bytes, limit: int) -> bytes:
    try:
        decoder = bz2.BZ2Decompressor()
        result = decoder.decompress(data, max_length=limit + 1)
    except (EOFError, OSError, ValueError) as exc:
        raise PatchError("Invalid BSDIFF40 bzip2 block.") from exc
    if len(result) > limit or not decoder.eof or decoder.unused_data:
        raise PatchError("Oversized, truncated, or trailing BSDIFF40 block data.")
    return result


def apply_bsdiff(old: bytes, patch: bytes, expected_size: int) -> bytes:
    """Apply the BSDIFF40 wire format without external programs or packages."""
    if len(patch) < 32 or patch[:8] != b"BSDIFF40":
        raise PatchError("Not a BSDIFF40 patch.")
    control_size = read_offset(patch, 8)
    diff_size = read_offset(patch, 16)
    result_size = read_offset(patch, 24)
    if min(control_size, diff_size, result_size) < 0:
        raise PatchError("Negative BSDIFF40 block size.")
    if result_size != expected_size or result_size > MAX_DEX_SIZE:
        raise PatchError("Unexpected BSDIFF40 output size.")
    split1 = 32 + control_size
    split2 = split1 + diff_size
    if split1 > len(patch) or split2 > len(patch):
        raise PatchError("BSDIFF40 block extends beyond the patch.")
    controls = decompress_block(patch[32:split1], MAX_CONTROL_SIZE)
    differences = decompress_block(patch[split1:split2], result_size)
    extra = decompress_block(patch[split2:], result_size)
    if len(controls) % 24:
        raise PatchError("Invalid BSDIFF40 control stream length.")
    result = bytearray(result_size)
    old_position = new_position = control_position = diff_position = extra_position = 0
    while new_position < result_size:
        if control_position + 24 > len(controls):
            raise PatchError("Missing BSDIFF40 control tuple.")
        add = read_offset(controls, control_position)
        insert = read_offset(controls, control_position + 8)
        seek = read_offset(controls, control_position + 16)
        control_position += 24
        if add < 0 or insert < 0:
            raise PatchError("Negative BSDIFF40 control tuple.")
        if new_position + add + insert > result_size:
            raise PatchError("BSDIFF40 output overflow.")
        if diff_position + add > len(differences) or extra_position + insert > len(extra):
            raise PatchError("Truncated BSDIFF40 diff or extra stream.")
        for i in range(add):
            source = old_position + i
            previous = old[source] if 0 <= source < len(old) else 0
            result[new_position + i] = (differences[diff_position + i] + previous) & 255
        new_position += add
        old_position += add
        diff_position += add
        result[new_position:new_position + insert] = extra[extra_position:extra_position + insert]
        new_position += insert
        extra_position += insert
        old_position += seek
    if (control_position, diff_position, extra_position) != (len(controls), len(differences), len(extra)):
        raise PatchError("Unused BSDIFF40 stream data.")
    return bytes(result)


def load_manifest(directory: Path) -> dict:
    try:
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if manifest["schema"] != 1:
            raise PatchError("Unsupported patch manifest schema.")
        patch_path = (directory / manifest["dex"]["patch_file"]).resolve()
        if not patch_path.is_relative_to(directory.resolve()):
            raise PatchError("Patch file must be inside the patches directory.")
        patch = patch_path.read_bytes()
        require_hash(patch, manifest["dex"]["patch_sha256"], "Binary patch")
        if not 0 < manifest["dex"]["target_size"] <= MAX_DEX_SIZE:
            raise PatchError("Invalid target DEX size.")
        manifest["_patch_data"] = patch
        return manifest
    except (KeyError, TypeError, ValueError, OSError) as exc:
        raise PatchError(f"Cannot load patch manifest: {exc}") from exc


def make_replacements(archive: zipfile.ZipFile, manifest: dict) -> dict[str, bytes]:
    dex_spec, native_spec = manifest["dex"], manifest["native"]
    original_dex = archive.read(dex_spec["member"])
    require_hash(original_dex, dex_spec["source_sha256"], "Original DEX")
    patched_dex = apply_bsdiff(original_dex, manifest["_patch_data"], dex_spec["target_size"])
    require_hash(patched_dex, dex_spec["target_sha256"], "Patched DEX")
    original_native = archive.read(native_spec["member"])
    require_hash(original_native, native_spec["source_sha256"], "Original native library")
    offset = native_spec["file_offset"]
    before, after = bytes.fromhex(native_spec["before_hex"]), bytes.fromhex(native_spec["after_hex"])
    if offset < 0 or len(before) != len(after) or original_native[offset:offset + len(before)] != before:
        raise PatchError("Native instruction precondition failed.")
    patched_native = original_native[:offset] + after + original_native[offset + len(before):]
    require_hash(patched_native, native_spec["target_sha256"], "Patched native library")
    return {dex_spec["member"]: patched_dex, native_spec["member"]: patched_native}


def aligned_info(entry: zipfile.ZipInfo, current_offset: int) -> zipfile.ZipInfo:
    """Pad valid ZIP extra fields so stored entries are aligned before signing."""
    info = copy.copy(entry)
    if info.compress_type != zipfile.ZIP_STORED:
        return info
    alignment = 16384 if info.filename.endswith(".so") else 4
    name_bytes = info.filename.encode("ascii" if info.filename.isascii() else "utf-8")
    start = current_offset + 30 + len(name_bytes) + len(info.extra)
    needed = (-start) % alignment
    if needed:
        payload = (needed - 4) % alignment
        info.extra += struct.pack("<HH", 0xFFFF, payload) + b"\0" * payload
    if len(info.extra) > 65535:
        raise PatchError("ZIP extra field would exceed its format limit.")
    return info


def write_unsigned(archive: zipfile.ZipFile, target: Path, replacements: dict[str, bytes]) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as result:
        result.comment = archive.comment
        for entry in archive.infolist():
            if SIGNATURE_ENTRY.fullmatch(entry.filename):
                continue
            data = replacements.get(entry.filename)
            if data is None:
                data = archive.read(entry)
            result.writestr(aligned_info(entry, result.fp.tell()), data)


def verify_payload(source: zipfile.ZipFile, target: Path, replacements: dict[str, bytes]) -> dict:
    with zipfile.ZipFile(target) as result:
        if result.testzip() is not None:
            raise PatchError("Output ZIP integrity check failed.")
        old = {n for n in source.namelist() if not SIGNATURE_ENTRY.fullmatch(n)}
        new = {n for n in result.namelist() if not SIGNATURE_ENTRY.fullmatch(n)}
        if old != new:
            raise PatchError("Unexpected APK entry added or removed.")
        changed = []
        for name in sorted(old):
            expected = replacements[name] if name in replacements else source.read(name)
            data = result.read(name)
            if data != expected:
                raise PatchError(f"Output content mismatch: {name}")
            if name in replacements:
                changed.append(name)
        return {"changed_payload_entries": changed,
                "unchanged_payload_entries": len(old) - len(changed),
                "patched_member_sha256": {name: sha256(data) for name, data in replacements.items()}}


def run_tool(command: list[str], env: dict | None = None) -> str:
    try:
        completed = subprocess.run(command, capture_output=True, text=True, env=env, check=False)
    except OSError as exc:
        raise PatchError(f"Cannot run signing tool: {exc}") from exc
    if completed.returncode:
        raise PatchError(f"Signing tool failed ({Path(command[0]).name}):\n{completed.stdout}\n{completed.stderr}")
    return completed.stdout


def sign_apk(unsigned: Path, output: Path, args: argparse.Namespace) -> str:
    tools = args.build_tools.resolve()
    signer = tools / "lib" / "apksigner.jar"
    aligner = tools / ("zipalign.exe" if os.name == "nt" else "zipalign")
    if not signer.is_file() or not aligner.is_file():
        raise PatchError("Build Tools directory must contain zipalign and lib/apksigner.jar.")
    if not args.keystore.is_file():
        raise PatchError("Keystore does not exist. Create your own key using the README instructions.")
    env = os.environ.copy()
    if args.ks_pass_env:
        if args.ks_pass_env not in env:
            raise PatchError("The keystore-password environment variable is not set.")
        store_password = env[args.ks_pass_env]
    else:
        store_password = getpass.getpass("Keystore password: ")
    if args.key_pass_env:
        if args.key_pass_env not in env:
            raise PatchError("The key-password environment variable is not set.")
        key_password = env[args.key_pass_env]
    else:
        key_password = store_password
    env["LENS_PATCH_INTERNAL_STORE_PASS"] = store_password
    env["LENS_PATCH_INTERNAL_KEY_PASS"] = key_password
    aligned = unsigned.parent / "aligned.apk"
    run_tool([str(aligner), "-P", "16", "-f", "4", str(unsigned), str(aligned)])
    run_tool([args.java, "-jar", str(signer), "sign", "--v1-signing-enabled", "true",
              "--v2-signing-enabled", "true", "--v3-signing-enabled", "false",
              "--v4-signing-enabled", "false", "--ks", str(args.keystore.resolve()),
              "--ks-key-alias", args.alias, "--ks-pass", "env:LENS_PATCH_INTERNAL_STORE_PASS",
              "--key-pass", "env:LENS_PATCH_INTERNAL_KEY_PASS", "--out", str(output), str(aligned)], env)
    signature = run_tool([args.java, "-jar", str(signer), "verify", "--verbose", str(output)])
    run_tool([str(aligner), "-c", "-P", "16", "4", str(output)])
    return signature


def publish_file(source: Path, destination: Path) -> None:
    """Never overwrite a pre-existing APK, including during a concurrent run."""
    try:
        os.link(source, destination)
    except FileExistsError as exc:
        raise PatchError("Output already exists; choose a new filename.") from exc
    except OSError:
        created = False
        try:
            with destination.open("xb") as output, source.open("rb") as original:
                created = True
                shutil.copyfileobj(original, output)
        except FileExistsError as exc:
            raise PatchError("Output already exists; choose a new filename.") from exc
        except BaseException:
            if created:
                destination.unlink(missing_ok=True)
            raise


def build(args: argparse.Namespace, patch_directory: Path = ROOT / "patches") -> dict:
    manifest = load_manifest(patch_directory)
    original = args.input.resolve()
    output = args.output.resolve() if args.output else None
    if output == original or (output and output.exists()):
        raise PatchError("Output must be a new path different from the input APK.")
    if args.keystore and not args.build_tools:
        raise PatchError("Signing requires --build-tools.")
    if args.build_tools and not args.keystore:
        raise PatchError("Specify --keystore to request signing; otherwise omit --build-tools.")
    with original.open("rb") as handle:
        digest = hashlib.file_digest(handle, "sha256").hexdigest() if hasattr(hashlib, "file_digest") else None
        if digest is None:
            handle.seek(0)
            digest = sha256(handle.read())
        if digest != manifest["source_apk"]["sha256"]:
            raise PatchError(f"Unsupported APK. Required SHA-256: {manifest['source_apk']['sha256']}; got {digest}.")
        handle.seek(0)
        with zipfile.ZipFile(handle) as source:
            replacements = make_replacements(source, manifest)
            report = {"patcher_version": VERSION, "input_sha256": digest,
                      "application_version": manifest["source_apk"]["version_name"],
                      "architecture": manifest["source_apk"]["architecture"],
                      "patched_member_sha256": {name: sha256(data) for name, data in replacements.items()}}
            if args.verify_only:
                report["status"] = "input_and_patch_verified"
                return report
            if output is None:
                raise PatchError("Use --output for a build, or --verify-only for validation.")
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix=".lens-patch-", dir=output.parent) as scratch:
                work = Path(scratch).resolve()
                if work.parent != output.parent:
                    raise PatchError("Unexpected temporary directory location.")
                unsigned = work / "unsigned.apk"
                write_unsigned(source, unsigned, replacements)
                staged = unsigned
                if args.keystore:
                    staged = work / "signed.apk"
                    report["signature_verification"] = sign_apk(unsigned, staged, args).strip()
                report.update(verify_payload(source, staged, replacements))
                report["output_sha256"] = sha256(staged.read_bytes())
                report["status"] = "signed_and_verified" if args.keystore else "unsigned_requires_signing"
                publish_file(staged, output)
            report_path = output.with_suffix(output.suffix + ".json")
            # Metadata is not permitted to overwrite existing user files either.
            try:
                with report_path.open("x", encoding="utf-8") as stream:
                    json.dump(report, stream, indent=2)
                    stream.write("\n")
            except FileExistsError:
                print("Note: existing report was preserved; verification is printed below.", file=sys.stderr)
            return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="The exact supported original APK; never modified")
    parser.add_argument("-o", "--output", type=Path, help="New APK filename")
    parser.add_argument("--verify-only", action="store_true", help="Validate input and patch without writing an APK")
    parser.add_argument("--keystore", type=Path, help="Your existing keystore; requests signing")
    parser.add_argument("--alias", default="lens-local", help="Signing-key alias (default: lens-local)")
    parser.add_argument("--build-tools", type=Path, help="Android SDK Build Tools directory (36.0.0 tested)")
    parser.add_argument("--java", default="java", help="Java executable for apksigner")
    parser.add_argument("--ks-pass-env", help="Environment-variable name containing the store password")
    parser.add_argument("--key-pass-env", help="Environment-variable name containing a distinct key password")
    parser.add_argument("--version", action="version", version=VERSION)
    args = parser.parse_args(argv)
    try:
        report = build(args)
    except (PatchError, OSError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    if report["status"] == "unsigned_requires_signing":
        print("Unsigned APK: sign it with your own key before installation.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
