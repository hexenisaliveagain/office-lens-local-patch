"""Maintainer only: generate a delta from the original and validated reference APK."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import bsdiff4


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("reference", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    digest = lambda data: hashlib.sha256(data).hexdigest()
    expected = "c1bb0c9b881b65ff998c572944b6f40c90531fcedc2a2608507c11ed90cdf732"
    if digest(args.original.read_bytes()) != expected:
        raise ValueError("Unsupported original APK")
    with zipfile.ZipFile(args.original) as old, zipfile.ZipFile(args.reference) as new:
        dex = "classes5.dex"
        native = "lib/arm64-v8a/libplat.so"
        old_dex, new_dex = old.read(dex), new.read(dex)
        old_native, new_native = old.read(native), new.read(native)
        if digest(new_dex) != "4f62140a7d003f31f68577c025f0214818d6e938ad99435ebed5b266bae892bc":
            raise ValueError("Unexpected reference DEX")
        if digest(new_native) != "481732a88c41e74f9e2a842ec31cbfcbd679c4267ad4faddf28e014b62bb5655":
            raise ValueError("Unexpected reference native library")
        delta = bsdiff4.diff(old_dex, new_dex)
        manifest = {"schema": 1, "source_apk": {"sha256": expected,
            "package": "com.microsoft.office.officelens", "version_name": "16.0.19628.20008",
            "version_code": 2004969699, "architecture": "arm64-v8a"},
            "dex": {"member": dex, "source_sha256": digest(old_dex),
                "target_sha256": digest(new_dex), "target_size": len(new_dex),
                "patch_file": "classes5.bsdiff", "patch_sha256": digest(delta)},
            "native": {"member": native, "source_sha256": digest(old_native),
                "target_sha256": digest(new_native), "file_offset": 0xbda7c,
                "before_hex": "1f0100f9", "after_hex": "1f2003d5"}}
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "classes5.bsdiff").write_bytes(delta)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"delta_bytes": len(delta), "sha256": digest(delta)}))


if __name__ == "__main__":
    main()
