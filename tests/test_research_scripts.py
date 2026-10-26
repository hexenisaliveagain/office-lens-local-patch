"""Synthetic fixtures only; no application source or APK is a test fixture."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'tools/research/patch_smali.py'
STAGE = 'Lcom/microsoft/office/officelens/scansMigration/LensMigrationStage;'
METHODS = {
    'scansMigration/FREManager.smali': ['getMigrationStage()'+STAGE, 'shouldShowFRE()Z'],
    'utils/CommonUtils.smali': ['isLensMigrationEndOfLifeEnabled()Z'],
    'scansMigration/OneDriveMigrationFragment.smali': ['onGotoOneDriveClicked(Landroid/content/Context;'+STAGE+')V'],
    'scansMigration/OneDriveMigrationActivity.smali': ['onMAMCreate(Landroid/os/Bundle;)V'],
}

class ResearchScriptTests(unittest.TestCase):
    def fixture(self, root):
        shutil.copy2(SCRIPT, root/'patch_smali.py')
        code = root/'decoded/smali_classes5/com/microsoft/office/officelens'
        for name, signatures in METHODS.items():
            path=code/name;path.parent.mkdir(parents=True,exist_ok=True)
            # Deliberately synthetic parser text, not assembled application code.
            text='.class public Lsynthetic/Stub;\n.super Ljava/lang/Object;\n'
            for signature in signatures:
                text += '.method public '+signature+'\n    .locals 0\n    return-void\n.end method\n'
            path.write_text(text,encoding='utf-8')
        return code

    def test_five_replacements_preserve_method_headers_and_backups(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);code=self.fixture(root)
            originals={name:(code/name).read_text('utf-8') for name in METHODS}
            result=subprocess.run([sys.executable,str(root/'patch_smali.py')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(len(json.loads((root/'method-changes.json').read_text()) ),5)
            for name, signatures in METHODS.items():
                after=(code/name).read_text('utf-8')
                for signature in signatures:self.assertEqual(after.count('.method public '+signature+'\n'),1)
                self.assertEqual((root/'smali-original'/name).read_text('utf-8'),originals[name])
            self.assertIn('->PreMigration:',(code/'scansMigration/FREManager.smali').read_text())
            self.assertIn('->finish()V',(code/'scansMigration/OneDriveMigrationActivity.smali').read_text())

    def test_missing_signature_is_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);code=self.fixture(root)
            path=code/'scansMigration/FREManager.smali'
            path.write_text(path.read_text().replace('getMigrationStage()','unsupportedVersion()'))
            result=subprocess.run([sys.executable,str(root/'patch_smali.py')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Expected exactly one',result.stderr)

if __name__=='__main__':unittest.main()
