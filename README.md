# Lens local patch

Unofficial offline patch for Microsoft Lens **16.0.19628.20008 / 2004969699, ARM64**.
Removes the forced OneDrive migration screen and its external app/store redirect,
and includes the native crash fix validated in FIX1. Microsoft does not endorse this project.

[Instrukcja po polsku](README-PL.md) · [Technical changes](TECHNICAL.md)

## Download

[Download the ready-to-use ZIP (v1.1.0)](https://github.com/hexenisaliveagain/office-lens-local-patch/releases/download/v1.1.0/Lens-local-patch-1.1.0-source.zip)
and [its SHA-256 checksum](https://github.com/hexenisaliveagain/office-lens-local-patch/releases/download/v1.1.0/Lens-local-patch-1.1.0-source.zip.sha256).
Extract the ZIP and follow the commands below. [All releases](https://github.com/hexenisaliveagain/office-lens-local-patch/releases).

## Requirements

* Python 3.10 or newer, with bzip2 support. Applying the patch needs only the standard library.
* Your own copy of the exact original APK. No original or modified APK is included.
* For installation: JDK 17+ and Android SDK Build Tools (36.0.0 tested), and your own signing key.

Required original APK SHA-256:

```text
c1bb0c9b881b65ff998c572944b6f40c90531fcedc2a2608507c11ed90cdf732
```

Other builds, ABIs, split APK sets and previously modified APKs are rejected. The input is never overwritten.

## Windows wizard

Extract the ZIP and double-click **`Start-Windows.cmd`**. Select Polish or English, then:

1. Choose the original APK. Its compatibility is checked before creating a signing key.
2. Confirm detected JDK / Android SDK Build Tools, or select their locations.
3. Create a personal PKCS12 key, or select your existing keystore and key alias.
4. Choose a new output APK filename and enter your keystore password when prompted.

The wizard builds, aligns, signs and verifies the APK. It also supports existing keys with
separate private-key passwords. Keep a private backup of your key and password for future updates.
It never installs/uninstalls apps. Cancelling a file dialog exits; any key already created is retained.
If signing fails after creating a key, keep that key and choose the existing-key option on retry.
Existing APKs and keys are not overwritten. A Tk file-dialog failure falls back to console path input.

Install Python 3.10+ from [python.org](https://www.python.org/downloads/windows/) (enable **Add Python to PATH**),
JDK 17+, and Android SDK Build Tools (36.0.0 tested) first. The wizard detects `JAVA_HOME`/`PATH` and
`%LOCALAPPDATA%/Android/Sdk/build-tools`; tools installed elsewhere can be selected manually.
Build Tools can be installed through Android Studio's SDK Manager. The wizard does not download dependencies.

## Apply and sign

Run commands from the extracted project directory. Replace the example paths with your own.

```sh
python patch_lens.py original.apk --verify-only
```

Create a personal signing key once (keytool prompts for its password). Keep a private backup;
reuse the same key for your future patched releases. Never commit or share it.

```sh
keytool -genkeypair -keystore my-lens.p12 -storetype PKCS12 -alias lens-local -keyalg RSA -keysize 2048 -validity 10000
```

Build, align, sign and verify:

```sh
python patch_lens.py original.apk -o Lens-local.apk --keystore my-lens.p12 --build-tools "/path/to/Android/Sdk/build-tools/36.0.0"
```

On Windows, `--build-tools` can point to `C:/Users/YOUR_NAME/AppData/Local/Android/Sdk/build-tools/36.0.0`.
Use `--java "/path/to/jdk/bin/java"` if your default Java is older than 17.
The script prompts for the keystore password. For automation, `--ks-pass-env NAME`
reads the password from that environment variable; `--key-pass-env NAME` supports a separate key password.
The JSON report beside the output contains hashes, payload comparisons and signature verification.

To build without SDK tools, omit `--keystore` and `--build-tools`:

```sh
python patch_lens.py original.apk -o Lens-unsigned.apk
```

That output is **unsigned and cannot be installed** until aligned and signed. The integrated
signing path runs zipalign before apksigner, then checks alignment and signatures, as required by
the [Android signing documentation](https://developer.android.com/tools/apksigner).

## Install

Back up/export your scans first. A personal signature differs from Microsoft's, so replacing the
official app requires uninstalling it; uninstalling deletes its private app data.
An existing patched installation also needs reinstalling if its signing key differs.

```sh
adb uninstall com.microsoft.office.officelens
adb install Lens-local.apk
```

These are manual commands; the patcher never uninstalls an app or operates a phone.
Keep your key to install future patched updates with the same signer.
See [Android app signing](https://developer.android.com/studio/publish/app-signing).

## Verification and limits

Every build checks the original APK hash, delta hash, original and target component hashes,
ZIP integrity, and every payload entry. Only `classes5.dex` and `lib/arm64-v8a/libplat.so`
change; signature metadata is regenerated. The other 2,581 payload entries remain byte-identical.
ZIP compression and signature metadata can make whole-output hashes differ between environments.

The target payload was tested on a physical Samsung SM-S721B, Android 16: fresh image import,
editing completion, local PDF export, return to camera, and 4 min 35 s process survival without a
new fatal/native crash. This does not establish compatibility with every device. In particular,
realme GT Master Edition / realme UI 4.0 has not been verified on hardware.
The patch does not restore Microsoft's retired servers or guarantee online OCR/cloud services.
Normal optional cloud export UI remains available.

## Publish this method

Upload this source directory (or the supplied source ZIP) to your repository and attach it as a release.
Include both `patches/manifest.json` and `patches/classes5.bsdiff`; users supply their original APK
and signing key locally. Describe the exact supported version and hashes. Do not upload your APK,
keystore, passwords, SDK, extracted libraries or personal device logs. Review the release contents
before publishing. This package does not upload anything automatically.

Run synthetic tests with:

```sh
python -m unittest discover -s tests -v
```

Maintainers can regenerate the BSDIFF40 delta using `tools/build_patch.py ORIGINAL REFERENCE OUTPUT`,
with `bsdiff4==1.2.6` installed. This optional dependency is not needed by users. The generator accepts
only the pinned original APK and validated reference component hashes. BSDIFF40 format:
[Colin Percival's bsdiff](https://www.daemonology.net/bsdiff/).

The MIT license covers this project's original code and documentation. It grants no rights to
Microsoft's application, trademarks or other third-party material. No Microsoft APK is supplied.
