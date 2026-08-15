"""PS-20 (D-14) — Router **Matriks Persetujuan yang mengikat** + antrean "Persetujuan Saya".

  GET /api/approvals/matrix       — matriks + tingkat + kebijakan penegakan yang berlaku
  GET /api/approvals/my-queue     — dokumen yang menunggu keputusan saya (4 tahap)
  GET /api/approvals/matrix-log   — jejak keputusan & pelanggaran (audit)

Akses: peran penilai/approver (admin/manager) — sama seperti layar Divisi & Persetujuan.
Keputusan tetap dilakukan di endpoint aslinya (rnd/specs, rnd/samples, PR, special-orders)
supaya tidak ada dua jalur penulisan status.
"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from dependencies import require_permission
from entity_scope import entity_ctx
from services import approval_matrix_service as amx

router = APIRouter(prefix="/api")

APPROVER_ROLES = ("admin", "manager")


def _assert_approver(actor: Dict[str, Any]) -> None:
    if (actor or {}).get("role") not in APPROVER_ROLES:
        raise HTTPException(status_code=403,
                            detail="Hanya admin/manager (approver) yang dapat membuka "
                                   "antrean & matriks persetujuan.")


def _eid(entity_id: Optional[str], ctx) -> str:
    return entity_id if entity_id and entity_id != "all" else ctx.active_entity_id


@router.get("/approvals/matrix")
async def get_matrix(request: Request,
                     entity_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    actor = await require_permission(request, "rnd", "view")
    _assert_approver(actor)
    ctx = await entity_ctx(request)
    return await amx.matrix(_eid(entity_id, ctx) or "")


@router.get("/approvals/my-queue")
async def get_my_queue(request: Request,
                       stage: Optional[str] = Query(None),
                       entity_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    actor = await require_permission(request, "rnd", "view")
    _assert_approver(actor)
    ctx = await entity_ctx(request)
    if stage and stage not in amx.STAGE_BY_ID:
        raise HTTPException(status_code=400, detail="Tahap persetujuan tidak dikenal.")
    return await amx.my_queue(actor, _eid(entity_id, ctx) or "", stage or "")


@router.get("/approvals/matrix-log")
async def get_matrix_log(request: Request,
                         stage: Optional[str] = Query(None),
                         only_violations: bool = Query(False),
                         limit: int = Query(50, ge=1, le=300),
                         entity_id: Optional[str] = Query(None)) -> Dict[str, Any]:
    actor = await require_permission(request, "rnd", "view")
    _assert_approver(actor)
    ctx = await entity_ctx(request)
    rows: List[Dict[str, Any]] = await amx.log(
        _eid(entity_id, ctx) or "", stage or "", limit, only_violations)
    return {"items": rows, "total": len(rows)}
