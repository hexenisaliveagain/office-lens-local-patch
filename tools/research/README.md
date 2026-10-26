# Original source transforms used during FIX1 research

These three original helper sources were not part of the public patcher release.
The end-user patcher, Windows wizard and pinned release payload already exist in
the repository; they are not republished here.

* `patch_smali.py` expresses the five migration method replacements as Python
  transformations. It preserves class and method identities. Only the authored
  replacement bodies and method identifiers are distributed, not decompiled files.
* `AssembleDex.java` invokes the external Google smali assembler at API level 24.
* `build_native_fix.py` verifies the exact historical TEST APK, ELF architecture,
  original library hash and ARM64 instruction before replacing the delayed JavaVM
  invalidation with NOP. It verifies the resulting instruction and unchanged DEX.

## Keep all generated application material outside the repository

These are historical workspace helpers, not a new end-user workflow. Copy them to
a separate private working directory before running them. They use paths relative
to their own location and produce local application files and analysis outputs.
Do not commit the private workspace, APK/DEX/SO, decoded smali, generated diffs,
disassembly, signing keys or device logs. The local ignore file is an additional
guard, not permission to upload generated material.

`patch_smali.py` expects a fresh decode under
`decoded/smali_classes5/com/microsoft/office/officelens`. It writes backups under
`smali-original`, a generated local `changes.diff`, and `method-changes.json`.
It is not transactional across files: use a disposable fresh private decode and
discard it if validation fails. Decode your own exact original APK with apktool;
apktool and the application's sources are not included here.

`AssembleDex` needs an external smali classpath providing
`com.android.tools.smali.smali`. Its arguments are the smali directory and output
DEX path. Assembly alone is not signing or validation. The original research used
apiLevel 24, four jobs and the existing five-method TEST payload.

`build_native_fix.py` expects the exact historical
`Lens-no-OneDrive-TEST-16.0.19628.20008.apk` in its private workspace. It is an
intermediate input, not the Microsoft-signed original or the final FIX1 APK.
It needs `pyelftools` and `capstone` available to Python (or in a private
`python-tools` folder). Run without Python's `-O` option: its research assertions
must remain enabled. It writes a private unsigned APK and analysis files to
`native-fix`; align and sign locally with your own tools and key.

For the maintained, hash-checked installation workflow use the root README and
`patch_lens.py`. The new files in this directory contain source transforms only.
The pre-existing `patches/classes5.bsdiff` belongs to that older release workflow;
as TECHNICAL.md explains, it may contain fragments of the changed binary. It is
not newly uploaded by this source-only supplement. Do not include it when making
an export that must contain only authored source.

## Polski

To brakujące skrypty źródłowe pierwotnej metody, a nie druga kopia wydania.
Uruchamiaj je po skopiowaniu do prywatnego katalogu poza repozytorium.
Nie publikuj wygenerowanych plików aplikacji, diffów z oryginalnym kodem,
kluczy ani logów telefonu. Gotowy, utrzymywany patcher jest opisany w README.
