# Changes and crash fix

The DEX delta reconstructs the validated FIX1 `classes5.dex` from the pinned original.
It contains five semantic method changes; classes are retained:

* `FREManager.getMigrationStage`: return the existing PreMigration enum value.
* `FREManager.shouldShowFRE`: return false.
* `CommonUtils.isLensMigrationEndOfLifeEnabled`: return false.
* `OneDriveMigrationFragment.onGotoOneDriveClicked`: return without starting external intents.
* `OneDriveMigrationActivity.onMAMCreate`: keep the superclass call, then finish the activity.

The native fix modifies `lib/arm64-v8a/libplat.so` at file offset **0xbda7c**:
`1f0100f9` (`str xzr, [x8]`) becomes `1f2003d5` (ARM64 `nop`). This offset is specific to
the original library hash in the manifest; never reuse it blindly on another release.

During `OfficeNativeHelpers::Initialize`, an obfuscated validation error path starts a worker.
After a randomized delay, that worker writes NULL into the shared JavaVM pointer. Subsequent
JNI telemetry/timer calls dereference that invalid pointer and crash. The patch prevents this one
write. JNI initialization, certificate comparisons, telemetry and timers remain in place.
The exact condition triggering the obfuscated validation path has not been fully established.
This is a bounded fix to the observed crash mechanism, not a guarantee that all future crashes vanish.

An independent DEX comparison of the validated reference covered 9,165 classes and 57,872 methods,
normalizing equivalent default static values and try-range encodings; only the five intended methods
changed semantically. Patcher output is required to match those validated component SHA-256 values.

The patcher removes old top-level JAR signature entries, rebuilds the ZIP, preserves other payloads,
and optionally aligns and signs it. APK Signing Blocks from the old ZIP are not copied.
Stored entries are aligned by the Python writer; integrated signing additionally uses official
`zipalign -P 16`, then apksigner v1/v2 signing and verification. Original native libraries are compressed.

This project includes a binary difference rather than full Microsoft application files. The delta
may contain fragments of the changed binary; do not describe it as containing no third-party bytes.
Hash verification detects mismatched inputs and corruption; it does not authenticate the publisher.
Obtain the patch source/release through a publisher you trust and inspect it before running.
