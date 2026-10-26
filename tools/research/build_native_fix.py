"""Remove the verified delayed JavaVM invalidation, retaining the minimal migration patch."""
from pathlib import Path
import hashlib
import io
import json
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'python-tools'))
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_ARM

BASE = ROOT / 'Lens-no-OneDrive-TEST-16.0.19628.20008.apk'
EXPECTED_APK = 'cd3bd45bf720f54ce2afa081e5995147f35f8cdab6d8da3b206012b849e20e2d'
EXPECTED_LIB = 'f4e4aee5483bf9817a7bb99e652858897da06a4d1b0afa4afcc83fe64ea85380'
MEMBER = 'lib/arm64-v8a/libplat.so'
ADDRESS = 0xbea7c
OLD = bytes.fromhex('1f0100f9')
NEW = bytes.fromhex('1f2003d5')
OUT = ROOT / 'native-fix'
OUT.mkdir(exist_ok=True)
assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED_APK

with zipfile.ZipFile(BASE) as z:
    original = z.read(MEMBER)
assert hashlib.sha256(original).hexdigest() == EXPECTED_LIB
elf = ELFFile(io.BytesIO(original))
assert elf['e_machine'] == 'EM_AARCH64'
offset = next(elf.address_offsets(ADDRESS))
assert offset == 0xbda7c
assert original[offset:offset+4] == OLD
decoder = Cs(CS_ARCH_ARM64, CS_MODE_ARM)
instruction = list(decoder.disasm(OLD, ADDRESS))
assert len(instruction) == 1 and instruction[0].mnemonic == 'str' and instruction[0].op_str == 'xzr, [x8]'
patched = original[:offset] + NEW + original[offset+4:]
assert len(patched) == len(original)
assert sum(a != b for a,b in zip(original, patched)) == sum(a != b for a,b in zip(OLD, NEW))
assert original[:offset] == patched[:offset] and original[offset+4:] == patched[offset+4:]
assert next(decoder.disasm(patched[offset:offset+4], ADDRESS)).mnemonic == 'nop'
(OUT / 'libplat.so').write_bytes(patched)

unsigned = OUT / 'Lens-no-OneDrive-FIX1-unsigned.apk'
signature = re.compile(r'META-INF/[^/]+\.(SF|RSA|DSA|EC|MF)', re.IGNORECASE)
with zipfile.ZipFile(BASE) as source, zipfile.ZipFile(unsigned, 'w') as dest:
    for entry in source.infolist():
        if signature.fullmatch(entry.filename):
            continue
        dest.writestr(entry, patched if entry.filename == MEMBER else source.read(entry))
with zipfile.ZipFile(unsigned) as candidate, zipfile.ZipFile(BASE) as base:
    assert candidate.testzip() is None
    changed = [n for n in candidate.namelist() if candidate.read(n) != base.read(n)]
    assert changed == [MEMBER], changed
    assert candidate.read('classes5.dex') == base.read('classes5.dex')

proof = {
    'base_apk': str(BASE), 'base_sha256': EXPECTED_APK,
    'library': MEMBER, 'original_library_sha256': EXPECTED_LIB,
    'patched_library_sha256': hashlib.sha256(patched).hexdigest(),
    'virtual_address': hex(ADDRESS), 'file_offset': hex(offset),
    'old_bytes': OLD.hex(), 'new_bytes': NEW.hex(),
    'old_instruction': 'str xzr, [x8]', 'new_instruction': 'nop',
    'reason': 'Verified delayed callback writes NULL to the shared JavaVM global at image+0x13bfe0; preserve the initialized VM for subsequent JNI callbacks.',
    'callback': '0xbe9d4', 'callback_reference': '0xbd9c4',
    'retained': ['all Java telemetry', 'native timer callbacks', 'JNI_OnLoad and JVMEnv.setJvm', 'five migration-method replacements'],
    'changed_payload_vs_test': changed,
}
(OUT / 'NATIVE-FIX.json').write_text(json.dumps(proof, indent=2), encoding='utf-8')
lines = []
start = next(elf.address_offsets(0xbe9d4))
for label,data in [('BEFORE', original), ('AFTER', patched)]:
    lines.append(label)
    lines.extend(f'{i.address:08x}: {i.mnemonic} {i.op_str}'
                 for i in decoder.disasm(data[start:start+0xbc], 0xbe9d4))
(OUT / 'native-fix-disassembly.txt').write_text('\n'.join(lines)+'\n', encoding='utf-8')
print(json.dumps(proof, indent=2))
