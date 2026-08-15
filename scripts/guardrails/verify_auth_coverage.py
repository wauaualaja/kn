#!/usr/bin/env python3
"""INV-AUTH-01 — Setiap endpoint router WAJIB menegakkan autentikasi.

Kelas bug yang dicegah (Sesi #076):
  * AUTH-DOC-PREVIEW (P0): GET /documents/preview/{id} → dokumen bisnis penuh TANPA login.
  * AUTH-MASTER-LEAK (P1): GET /products, /uoms, /warehouses, /pos/best-sellers TANPA login.

Aturan (STATIK, tidak butuh backend):
  Tiap `@router.<method>("<path>")` di backend/routers/*.py harus — baik langsung di badannya,
  ATAU via helper lokal (`_xxx(request)`) yang di dalamnya menegakkan auth — memanggil ENFORCER:
    - KERAS : require_permission | require_role      (login + otorisasi)
    - LUNAK : current_user | entity_ctx              (minimal login) — sah HANYA bila TIDAK
              ditelan try/except (menelan = 401 di-swallow → bocor, spt list_products).
  Delegasi ke helper lokal ditelusuri transitif (mis. /hr/kpi/me → _my_kpi → _emp_for_user →
  current_user). Endpoint benar-benar publik/ber-auth-khusus (device_token) didaftar EKSPLISIT
  di PUBLIC_ALLOWLIST + alasan.

Melanggar → MERAH: sebut file, `METHOD /path`, dan alasan.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _common import BACKEND, Guard  # noqa: E402

HARD = ("require_permission", "require_role")
SOFT = ("current_user", "entity_ctx")

PUBLIC_ALLOWLIST = {
    "POST /auth/login",             # gerbang login — wajib publik.
    "POST /auth/logout",            # idempotent: hapus sesi milik token yang dibawa; tak bisa disalahgunakan.
    "POST /hr/attendance/ingest",   # agen jembatan on-prem ZKTeco — auth via device_token (bukan sesi), cek eksplisit.
    "GET /verify/{code}",           # e-sign verifikasi publik (QR/halaman /verify-document) — by design tanpa login; hanya baca status by kode acak.
}

DEC_RE = re.compile(r'@router\.(get|post|patch|put|delete)\(\s*["\']([^"\']+)["\']')
DEF_RE = re.compile(r'^\s*(?:async\s+)?def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(')


def _indent(s):
    return len(s) - len(s.lstrip())


def _blocks(lines):
    """Yield (name, start, body_lines) untuk tiap fungsi def di file (endpoint & helper)."""
    idxs = [(i, m.group(1)) for i, ln in enumerate(lines) for m in [DEF_RE.match(ln)] if m]
    for k, (i, name) in enumerate(idxs):
        end = idxs[k + 1][0] if k + 1 < len(idxs) else len(lines)
        yield name, i, lines[i:end]


def swallowed(body, enforcer):
    """True bila panggilan enforcer berada dalam blok try: ... except ...: (401 ditelan)."""
    for j, ln in enumerate(body):
        if enforcer + "(" not in ln:
            continue
        ind = _indent(ln)
        try_ind = None
        for k in range(j - 1, -1, -1):
            s = body[k].strip()
            kind = _indent(body[k])
            if s == "try:" and kind < ind:
                try_ind = kind
                break
            if s.startswith("def ") and kind < ind:
                break
        if try_ind is None:
            continue
        for k in range(j + 1, len(body)):
            s = body[k].lstrip()
            kind = _indent(body[k])
            if kind == try_ind and s.startswith("except"):
                return True
            if s and kind < try_ind:
                break
    return False


def _direct_enforced(text, body):
    """True bila body ini langsung menegakkan auth (hard, atau soft tak-ditelan)."""
    if any(h + "(" in text for h in HARD):
        return True
    soft_hit = [s for s in SOFT if (s + "(") in text]
    if soft_hit and all(not swallowed(body, s) for s in soft_hit):
        return True
    return False


def _auth_helpers(blocks):
    """Set helper lokal (_xxx) yang menegakkan auth — transitif."""
    helper_body = {name: ("\n".join(b), b) for name, _, b in blocks if name.startswith("_")}
    auth = set()
    # pass langsung
    for name, (text, body) in helper_body.items():
        if _direct_enforced(text, body):
            auth.add(name)
    # pass transitif (helper memanggil helper auth)
    changed = True
    while changed:
        changed = False
        for name, (text, _) in helper_body.items():
            if name in auth:
                continue
            if any((h + "(") in text for h in auth):
                auth.add(name)
                changed = True
    return auth


def main() -> int:
    g = Guard("INV-AUTH-01", "Tiap endpoint router menegakkan auth (kecuali PUBLIC_ALLOWLIST)")
    for fp in sorted((BACKEND / "routers").glob("*.py")):
        if fp.name == "__init__.py":
            continue
        lines = fp.read_text().splitlines()
        blocks = list(_blocks(lines))
        helpers = _auth_helpers(blocks)
        # petakan baris dekorator → endpoint
        decs = [(i, m.group(1).upper(), m.group(2)) for i, ln in enumerate(lines)
                for m in [DEC_RE.search(ln)] if m]
        for idx, (i, method, path) in enumerate(decs):
            end = decs[idx + 1][0] if idx + 1 < len(decs) else len(lines)
            body = lines[i:end]
            text = "\n".join(body)
            key = f"{method} {path}"
            if key in PUBLIC_ALLOWLIST:
                continue
            g.bump()
            if _direct_enforced(text, body):
                continue
            if any((h + "(") in text for h in helpers):  # delegasi ke helper auth
                continue
            soft_hit = [s for s in SOFT if (s + "(") in text]
            if soft_hit:
                g.add(f"{fp.name}: `{key}` memakai {soft_hit} TAPI ditelan try/except → "
                      f"401 di-swallow (dapat diakses TANPA login). Angkat auth ke luar try / pakai require_permission.")
            else:
                g.add(f"{fp.name}: `{key}` TIDAK menegakkan auth (require_permission/require_role/current_user/entity_ctx) → "
                      f"dapat diakses TANPA login. Tambah enforcer atau daftarkan di PUBLIC_ALLOWLIST bila memang publik.")
    return g.finish()


if __name__ == "__main__":
    sys.exit(main())
