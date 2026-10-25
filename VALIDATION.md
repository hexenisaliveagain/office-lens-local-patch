# Release validation

Validated on Windows with Python 3.12, JDK 21 and Android SDK Build Tools 36.0.0.
The supplied workflow makes synthetic tests runnable on Linux, macOS and Windows;
only the local Windows run was executed for this release.

* Seven synthetic tests cover signed-magnitude BSDIFF40 integers, negative seeks,
  seek-only tuples, malformed/truncated streams, output and decompression bounds,
  corrupt patch manifests, path escape, refusal to overwrite an existing file,
  signature removal, UTF-8 ZIP filenames and stored-entry alignment.
* Real original APK -> unsigned output: all payloads verified; official zipalign check passed.
* Real original APK -> aligned and signed output: APK Signature Scheme v2 verified;
  official zipalign check passed. Signing used a private local key excluded from this package.
* Previously patched APK: rejected by the pinned original SHA-256 check.
* Both integration builds reconstructed the exact validated FIX1 component hashes
  recorded in `patches/manifest.json`; 2,581 other payloads remained identical.

BSDIFF40 delta size: 1,590,110 bytes.
Delta SHA-256: `bb44b03a2fe93cfe5182c4eb43320baac318e7ccdc5e0ce2de0d4796396276b6`.

This validates the public build process against the phone-tested FIX1 payload. The newly
repacked public-patcher output was not separately reinstalled during this release preparation.
For the prior physical-device test scope and limitations, see the README.
