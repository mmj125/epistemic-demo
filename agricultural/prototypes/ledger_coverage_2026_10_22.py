"""Lists module-level constants and functions of cycles_engine_validate.py that PROVENANCE_LEDGER.md does not mention (diagnostics, forcing hooks and flags excluded)."""
import re,ast
led=open('/home/user/epistemic-demo/agricultural/PROVENANCE_LEDGER.md').read()
src=open('/home/user/epistemic-demo/agricultural/prototypes/cycles_engine_validate.py').read()
skip=re.compile(r'^(DIAG_|.*_FORCE$|.*_FORCE_|FORCE_|CFORCE|THETA_FORCE|NPOOL_|NLAYER_|N_SOLVE_DEBUG|N_UNMET|REFERENCE_DATA_DIR|SIXPOOL_DIAG|_)')
names=[m.group(1) for m in re.finditer(r'^([A-Z][A-Z0-9_]+)(?:\s*,\s*[A-Z][A-Z0-9_]+)*\s*=\s*[^=]',src,re.M)]
allnames=set()
for l in src.split('\n'):
    m=re.match(r'^([A-Z][A-Z0-9_]+(?:\s*,\s*[A-Z][A-Z0-9_]+)*)\s*=\s*[^=]',l)
    if m: allnames.update(x.strip() for x in m.group(1).split(','))
prefixes=re.findall(r'([A-Z][A-Z0-9_]*_)\*',led)
def mentioned(n):
    if any(n.startswith(p) for p in prefixes): return True
    stem=n
    while stem:
        if stem in led: return True
        if '_' not in stem: return False
        stem=stem.rsplit('_',1)[0]
        if len(stem)<5: return False
    return False
unc=sorted(n for n in allnames if not skip.match(n) and not mentioned(n))
print(f"{len(allnames)} constants, {len(unc)} not mentioned in the ledger (by name or name stem):"); print(', '.join(unc))
funcs=[n.name for n in ast.parse(src).body if isinstance(n,ast.FunctionDef) and not n.name.startswith('_')]
fu=sorted(f for f in funcs if f not in led)
print(f"{len(funcs)} functions, {len(fu)} not mentioned:"); print(', '.join(fu))
