"""Apply five bounded method replacements, preserving class and method identities."""
from pathlib import Path
import difflib
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parent
CODE = ROOT / 'decoded' / 'smali_classes5' / 'com/microsoft/office/officelens'
STAGE = 'Lcom/microsoft/office/officelens/scansMigration/LensMigrationStage;'
PATCHES = [
    ('scansMigration/FREManager.smali', 'getMigrationStage()' + STAGE,
     f'    .locals 1\n\n    sget-object v0, {STAGE}->PreMigration:{STAGE}\n\n    return-object v0\n'),
    ('scansMigration/FREManager.smali', 'shouldShowFRE()Z',
     '    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0\n'),
    ('utils/CommonUtils.smali', 'isLensMigrationEndOfLifeEnabled()Z',
     '    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0\n'),
    ('scansMigration/OneDriveMigrationFragment.smali',
     'onGotoOneDriveClicked(Landroid/content/Context;' + STAGE + ')V',
     '    .locals 0\n\n    return-void\n'),
    ('scansMigration/OneDriveMigrationActivity.smali', 'onMAMCreate(Landroid/os/Bundle;)V',
     '    .locals 0\n\n'
     '    invoke-super {p0, p1}, Landroidx/fragment/app/FragmentActivity;->onMAMCreate(Landroid/os/Bundle;)V\n\n'
     '    invoke-virtual {p0}, Landroid/app/Activity;->finish()V\n\n'
     '    return-void\n'),
]

originals = {}
changes = []
for relative, signature, body in PATCHES:
    path = CODE / relative
    before = path.read_text(encoding='utf-8')
    originals.setdefault(path, before)
    pattern = r'(^\.method [^\n]* ' + re.escape(signature) + r'\n).*?^\.end method'
    after, count = re.subn(pattern, lambda m: m[1] + body + '.end method', before,
                           flags=re.MULTILINE | re.DOTALL)
    if count != 1:
        raise RuntimeError(f'Expected exactly one {relative}:{signature}, got {count}')
    path.write_text(after, encoding='utf-8', newline='\n')
    changes.append({'file': relative, 'method': signature})

diff = []
for path, before in originals.items():
    relative = path.relative_to(CODE).as_posix()
    backup = ROOT / 'smali-original' / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    backup.write_text(before, encoding='utf-8', newline='\n')
    after = path.read_text(encoding='utf-8')
    diff.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                    fromfile='original/' + relative, tofile='patched/' + relative))
(ROOT / 'changes.diff').write_text(''.join(diff), encoding='utf-8')
(ROOT / 'method-changes.json').write_text(json.dumps(changes, indent=2), encoding='utf-8')
print(json.dumps({'modified_files': len(originals), 'modified_methods': changes}, indent=2))
