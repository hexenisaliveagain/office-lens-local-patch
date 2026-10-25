import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import windows_wizard as w


class WizardTests(unittest.TestCase):
    def test_incompatible_apk_stops_before_signing_setup(self):
        with patch.object(w, "pick", return_value=Path("original.apk")) as choose, \
             patch("builtins.input", return_value="2"), \
             patch.object(w.patch_lens, "main", return_value=2) as patcher, \
             patch.object(w, "java_candidate") as java, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(w.wizard(), 2)
            self.assertEqual(choose.call_count, 1)
            self.assertEqual(patcher.call_count, 1)
            java.assert_not_called()

    def test_existing_key_flow_requests_signed_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = root / "sdk"
            (tools / "lib").mkdir(parents=True)
            (tools / "zipalign.exe").touch()
            (tools / "lib/apksigner.jar").touch()
            key = root / "my key.p12"
            key.touch()
            original, output = root / "original.apk", root / "patched.apk"
            with patch.object(w, "pick", side_effect=[original, key, output]), \
                 patch("builtins.input", side_effect=["2", "", "2", "custom-alias", "n"]), \
                 patch.object(w, "java_candidate", return_value=root / "java.exe"), \
                 patch.object(w, "java_major", return_value=21), \
                 patch.object(w, "sdk_candidate", return_value=tools), \
                 patch.object(w.patch_lens, "main", side_effect=[0, 0]) as patcher, \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(w.wizard(), 0)
                args = patcher.call_args_list[1].args[0]
                self.assertEqual(args[args.index("--keystore") + 1], str(key))
                self.assertEqual(args[args.index("--alias") + 1], "custom-alias")
                self.assertEqual(args[args.index("-o") + 1], str(output))
                self.assertIn("--build-tools", args)

    def test_java_version_formats(self):
        for version, expected in [('openjdk version "21.0.1"', 21), ('java version "1.8.0_442"', 8)]:
            with patch.object(w.subprocess, "run") as run:
                run.return_value.returncode = 0
                run.return_value.stderr = version
                run.return_value.stdout = ""
                self.assertEqual(w.java_major("java"), expected)

    def test_new_key_is_created_without_password_in_arguments(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "lib").mkdir()
            for name in ("zipalign.exe", "lib/apksigner.jar", "keytool.exe"):
                (root / name).touch()
            key = root / "new.p12"
            with patch.object(w, "pick", side_effect=[root/"original.apk", key, root/"out.apk"]), \
                 patch("builtins.input", side_effect=["1", "", "1", ""]), \
                 patch.object(w, "java_candidate", return_value=root / "java.exe"), \
                 patch.object(w, "java_major", return_value=21), \
                 patch.object(w, "sdk_candidate", return_value=root), \
                 patch.object(w.patch_lens, "main", side_effect=[0, 0]), \
                 patch.object(w.subprocess, "run") as keytool, \
                 contextlib.redirect_stdout(io.StringIO()):
                keytool.return_value.returncode = 0
                self.assertEqual(w.wizard(), 0)
                command = keytool.call_args.args[0]
                self.assertEqual(command[0], str(root/"keytool.exe"))
                self.assertEqual(command[command.index("-keystore")+1], str(key))
                self.assertIn("PKCS12", command)
                self.assertNotIn("-storepass", command)

    def test_cancel_is_clean(self):
        with patch.object(w, "wizard", side_effect=w.Cancelled), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(w.main(), 0)


if __name__ == "__main__":
    unittest.main()
