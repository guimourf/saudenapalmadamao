"""Fila única para operações: cria padrão se vazio; avisa se houver várias ativas."""
from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.models.queue import Queue

DEFAULT_QUEUE_NAME = "Fila padrão — atendimento"
DEFAULT_QUEUE_DESCRIPTION = (
    "Criada automaticamente. O sistema usa uma única fila ativa para todas as operações."
)


def _waiting_count(handle, queue_id: str) -> int:
    qid = (queue_id or "").strip()
    if not qid:
        return 0
    entries = handle.find("queue_entries", {"queue_id": qid})
    return sum(1 for e in entries if e.get("status") == "waiting")


def _pick_canonical_active_queue(
    handle, active: List[Dict[str, Any]]
) -> Dict[str, Any]:
    defaults = [q for q in active if q.get("is_default")]
    if len(defaults) == 1:
        return defaults[0]
    by_name = [q for q in active if (q.get("name") or "").strip() == DEFAULT_QUEUE_NAME]
    if len(by_name) == 1:
        return by_name[0]
    # Várias ativas sem marca única: usa a que tem mais em espera (evita fila operacional vazia
    # enquanto outra concentra pacientes). Empate: created_at mais antigo.
    scored = []
    for q in active:
        qid = q.get("queue_id") or q.get("id") or ""
        scored.append((q, _waiting_count(handle, qid), q.get("created_at", "") or ""))
    scored.sort(key=lambda x: (-x[1], x[2]))
    return scored[0][0]


def resolve_operation_queue(handle) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Retorna a fila usada em teleatendimento espontâneo, adicionar/remover/espera automática.
    - Nenhuma fila ativa: cria a padrão (is_default=True).
    - Uma fila ativa: usa ela.
    - Várias filas ativas: aviso; escolhe is_default único, ou nome padrão automático, ou
      a fila com mais entradas em espera (empate: mais antiga por created_at).
    """
    warnings: List[Dict[str, Any]] = []
    all_rows = handle.find("queues")
    active = [
        q
        for q in all_rows
        if (q.get("status") or "").strip().lower() == "active"
    ]

    if not active:
        queue = Queue(
            name=DEFAULT_QUEUE_NAME,
            description=DEFAULT_QUEUE_DESCRIPTION,
        )
        qd = queue.to_dict()
        qd["is_default"] = True
        handle.save("queues", qd)
        refreshed = handle.find("queues", {"queue_id": qd.get("queue_id")})
        return refreshed[0] if refreshed else qd, warnings

    if len(active) > 1:
        warnings.append(
            {
                "code": "multiple_active_queues",
                "severity": "warning",
                "message": (
                    "Existem mais de uma fila com status ativo. Recomenda-se desativar ou remover "
                    "as filas extras em fila_listar e manter apenas uma. Enquanto isso, todas as "
                    "operações automáticas usam a fila indicada em operational_queue."
                ),
                "active_queue_ids": [
                    q.get("queue_id") for q in sorted(
                        active, key=lambda x: x.get("created_at", "") or ""
                    )
                ],
                "active_queues": [
                    {
                        "queue_id": q.get("queue_id"),
                        "name": q.get("name"),
                        "is_default": bool(q.get("is_default")),
                    }
                    for q in sorted(active, key=lambda x: x.get("created_at", "") or "")
                ],
            }
        )

    chosen = _pick_canonical_active_queue(handle, active)
    return chosen, warnings
