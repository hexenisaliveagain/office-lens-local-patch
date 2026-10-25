"""Interactive Windows launcher; uses the verified offline patcher and SDK tools."""
from __future__ import annotations
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

if sys.version_info < (3, 10):
    raise SystemExit("Python 3.10+ required / Wymagany Python 3.10+")

import patch_lens


class Cancelled(Exception):
    pass


def text(pl, en, language):
    return pl if language == "pl" else en


def pick(title, kind="file", initial=None, extension=""):
    """Native file/folder dialog, with console fallback if Tk is unavailable."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            options = {"title": title, "parent": root}
            if initial:
                options["initialdir"] = str(initial if initial.is_dir() else initial.parent)
                if kind == "save":
                    options["initialfile"] = initial.name
            if kind == "folder":
                value = filedialog.askdirectory(**options)
            elif kind == "save":
                value = filedialog.asksaveasfilename(**options, defaultextension=extension)
            else:
                value = filedialog.askopenfilename(**options)
        finally:
            root.destroy()
    except Exception as exc:
        if not isinstance(exc, (ImportError, RuntimeError)) and type(exc).__name__ != "TclError":
            raise
        value = input(title + " (path / sciezka): ").strip().strip('"')
    if not value:
        raise Cancelled()
    return Path(value).expanduser().resolve()


def sdk_candidate():
    base = Path(os.environ.get("LOCALAPPDATA", "")) / "Android/Sdk/build-tools"
    candidates = [path for path in base.glob("*")
                  if (path / "zipalign.exe").is_file() and (path / "lib/apksigner.jar").is_file()]
    def version(path):
        return tuple(int(part) for part in re.findall(r"\d+", path.name))
    return max(candidates, key=version) if candidates else None


def java_candidate():
    home = os.environ.get("JAVA_HOME")
    candidate = Path(home) / "bin/java.exe" if home else None
    if candidate and candidate.is_file():
        return candidate
    found = shutil.which("java")
    return Path(found).resolve() if found else None


def java_major(executable):
    result = subprocess.run([str(executable), "-version"], capture_output=True, text=True, check=False)
    match = re.search(r'version "(\d+)(?:\.(\d+))?', result.stderr + result.stdout)
    if result.returncode or not match:
        raise patch_lens.PatchError("Cannot detect Java version / Nie mozna wykryc wersji Java")
    return int(match[2]) if match[1] == "1" else int(match[1])


def wizard():
    print("Lens local patch — Windows\n1. Polski\n2. English")
    language = "en" if input("> ").strip() == "2" else "pl"
    say = lambda pl, en: text(pl, en, language)
    print(say("Wybierz oryginalny APK. Anulowanie okna konczy kreator.",
              "Select the original APK. Cancel a dialog to exit."))
    original = pick(say("Oryginalny APK Lens", "Original Lens APK"))
    # Verify compatibility before creating a key or producing an APK.
    if patch_lens.main([str(original), "--verify-only"]):
        return 2
    print(say("Wymagane: JDK 17+ i Android SDK Build Tools (testowane 36.0.0).",
              "Required: JDK 17+ and Android SDK Build Tools (36.0.0 tested)."))
    java = java_candidate()
    if java is None or java_major(java) < 17:
        java = pick(say("Wybierz java.exe z JDK 17+", "Select java.exe from JDK 17+"))
    if java_major(java) < 17:
        raise patch_lens.PatchError("JDK 17+ required / Wymagany JDK 17+")
    tools = sdk_candidate()
    if tools:
        print(say("Wykryto SDK: ", "Detected SDK: ") + str(tools))
        if input(say("Enter: uzyj; 2: wybierz inny folder: ",
                     "Enter: use; 2: choose another folder: ")).strip() == "2":
            tools = None
    if tools is None:
        tools = pick(say("Folder Build Tools z zipalign.exe i lib/apksigner.jar",
                         "Build Tools folder containing zipalign.exe and lib/apksigner.jar"), "folder")
    if not (tools / "zipalign.exe").is_file() or not (tools / "lib/apksigner.jar").is_file():
        raise patch_lens.PatchError("Invalid Build Tools folder / Nieprawidlowy folder Build Tools")
    print(say("1. Utworz moj nowy klucz\n2. Uzyj mojego istniejacego klucza",
              "1. Create my new signing key\n2. Use my existing signing key"))
    existing = input("> ").strip() == "2"
    key = pick(say("Wybierz swoj klucz", "Select your keystore") if existing else
               say("Zapisz swoj nowy klucz PKCS12", "Save your new PKCS12 keystore"),
               "file" if existing else "save", extension=".p12")
    alias = input(say("Alias klucza [lens-local]: ", "Key alias [lens-local]: ")).strip() or "lens-local"
    if existing:
        if not key.is_file():
            raise patch_lens.PatchError("Keystore not found / Nie znaleziono klucza")
    else:
        if key.exists():
            raise patch_lens.PatchError("Will not overwrite a key / Nie nadpisze istniejacego klucza")
        keytool = java.parent / "keytool.exe"
        if not keytool.is_file():
            raise patch_lens.PatchError("Select a complete JDK with keytool.exe / Wybierz pelny JDK z keytool.exe")
        print(say("keytool zapyta o haslo i dane certyfikatu. Haslo nie jest zapisywane przez kreator.",
                  "keytool will ask for a password and certificate details. The wizard does not save the password."))
        result = subprocess.run([str(keytool), "-genkeypair", "-keystore", str(key), "-storetype",
                                 "PKCS12", "-alias", alias, "-keyalg", "RSA", "-keysize", "2048",
                                 "-validity", "10000"], check=False)
        if result.returncode:
            raise patch_lens.PatchError("Key generation failed / Tworzenie klucza nie powiodlo sie")
    print(say("Zachowaj prywatna kopie klucza i haslo. Ten sam klucz jest potrzebny do aktualizacji.",
              "Keep a private backup of your key and password. Reuse the same key for updates."))
    output = pick(say("Zapisz podpisany APK (nowa nazwa)", "Save the signed APK (new filename)"),
                  "save", original.with_name("Lens-local.apk"), ".apk")
    if output.exists() or output == original:
        raise patch_lens.PatchError("Output must be a new file / Wynik musi byc nowym plikiem")
    arguments = [str(original), "-o", str(output), "--keystore", str(key), "--alias", alias,
                 "--build-tools", str(tools), "--java", str(java)]
    # Existing JKS files may have a different private-key password.
    key_password_name = "LENS_WIZARD_KEY_PASSWORD"
    previous = os.environ.get(key_password_name)
    try:
        if existing and input(say("Inne haslo klucza niz magazynu? [t/N]: ",
                                  "Separate private-key password? [y/N]: ")).strip().lower() in {"t", "y"}:
            import getpass
            os.environ[key_password_name] = getpass.getpass(say("Haslo klucza: ", "Private-key password: "))
            arguments += ["--key-pass-env", key_password_name]
        print(say("Nakladanie laty i podpisywanie. Podaj haslo magazynu kluczy, gdy pojawi sie monit.",
                  "Patching and signing. Enter the keystore password when prompted."))
        result = patch_lens.main(arguments)
    finally:
        if previous is None:
            os.environ.pop(key_password_name, None)
        else:
            os.environ[key_password_name] = previous
    if result == 0:
        print(say("Gotowe. Podpisany APK: ", "Done. Signed APK: ") + str(output))
        print(say("Przed reinstalacja wyeksportuj skany. Odinstalowanie kasuje dane aplikacji.",
                  "Export scans before reinstalling. Uninstalling deletes app data."))
        print(say("Kreator nie instaluje aplikacji ani nie usuwa poprzedniej wersji.",
                  "The wizard does not install or uninstall apps."))
    return result


def main():
    try:
        return wizard()
    except (Cancelled, KeyboardInterrupt, EOFError):
        print("Anulowano / Cancelled")
        return 0
    except (patch_lens.PatchError, OSError) as exc:
        print("Blad / Error: " + str(exc), file=sys.stderr)
        print("Instrukcje / Instructions: README-PL.md, README.md", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
