"""Create a tracked task straight from an actionable inventory-reconciliation gap.

Task #60. From an *actionable* device-inventory reconciliation mismatch, a user
can explicitly create a tracked task that is pre-filled with the recommended
action + provenance and linked to the site (and device, when the mismatch names
one). The reconciliation read path stays strictly READ-ONLY — this is the only
write seam, and it never auto-creates: a task is created only on an explicit
request for a specific ``mismatch_signature``.

Design notes
------------
* The mismatch is re-resolved by re-running the read-only
  ``build_site_inventory_reconciliation`` and matching on the stable
  ``mismatch_signature`` (404 if the signature is unknown/stale).
* Only *actionable* mismatches are eligible: a recommended action must exist AND
  the acknowledgement policy must not be ``informational`` AND the blocking level
  must not be ``informational`` (422 otherwise). The frontend hides the button
  for non-actionable rows; this is the server-side backstop.
* Tasks land on the site's **Asset** board (inventory work is asset management),
  with the lowest-id board status as the default.
* Dedupe is per (site, ``mismatch_signature``) but only across **open** tasks
  (``completed_at IS NULL``). A closed task never blocks creating a fresh one, so
  a gap that re-appears after being resolved is trackable again.
* ``generated_at`` from the reconciliation is stored as provenance only — it is
  NOT part of the dedupe key (it changes on every read).
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.errors import UniqueConstraintViolationError
from app.crud.task import TaskCRUD
from app.helpers.task_tracker import TaskTrackerHandlerFactory
from app.models.board import Board, BoardModuleEnum, BoardRelatedEntity, BoardRelatedEntityTypeEnum
from app.models.site import Site
from app.models.task import Task, TaskPriorityEnum
from app.schema.inventory_reconciliation import InventoryAckPolicy, InventoryMismatch
from app.schema.task import InventoryMismatchTaskCreateSchema, InventoryMismatchTaskResponseSchema
from app.schema.user import CurrentUserSchema
from app.services.telemetry.device_inventory_reconciliation_service import (
    build_site_inventory_reconciliation,
)
from app.static import TaskMessages

logger = logging.getLogger(__name__)

#: Discriminator stored on ``tasks.source_kind`` for inventory-gap tasks.
INVENTORY_SOURCE_KIND = "inventory_reconciliation"

_INFORMATIONAL_BLOCKING = "informational"
_DEFAULT_DUE_DATE_OFFSET_DAYS = 7
_MAX_NAME_LENGTH = 250


def _is_actionable(mismatch: InventoryMismatch) -> bool:
    """A mismatch is actionable (task-eligible) only when it recommends a concrete
    next step that is not purely informational."""
    if not (mismatch.recommended_action and mismatch.recommended_action.strip()):
        return False
    if mismatch.acknowledgement_policy == InventoryAckPolicy.informational:
        return False
    blocking_value = getattr(mismatch.blocking_level, "value", mismatch.blocking_level)
    if blocking_value == _INFORMATIONAL_BLOCKING:
        return False
    return True


def _default_priority(mismatch: InventoryMismatch) -> TaskPriorityEnum:
    """Map blocking severity onto a task priority."""
    blocking_value = getattr(mismatch.blocking_level, "value", mismatch.blocking_level)
    if blocking_value == "blocks_calculation":
        return TaskPriorityEnum.high
    if blocking_value == "lowers_confidence":
        return TaskPriorityEnum.medium
    return TaskPriorityEnum.medium


def _default_name(mismatch: InventoryMismatch) -> str:
    return f"Inventory: {mismatch.title}"[:_MAX_NAME_LENGTH]


def _format_value(value) -> str:
    return "—" if value is None or value == "" else str(value)


def _build_description(site: Site, mismatch: InventoryMismatch) -> str:
    """A provenance-rich, standalone description so the task reads on its own."""
    blocking_value = getattr(mismatch.blocking_level, "value", mismatch.blocking_level)
    category_value = getattr(mismatch.category, "value", mismatch.category)
    equipment_value = getattr(mismatch.equipment_class, "value", mismatch.equipment_class)
    lines: list[Optional[str]] = [
        f"Inventory reconciliation follow-up for {site.name} (site #{site.id}).",
        f"Finding: {mismatch.title}.",
        mismatch.detail or None,
        f"Category: {category_value}." if category_value else None,
        f"Equipment class: {equipment_value}." if equipment_value else None,
        f"Impact: {str(blocking_value).replace('_', ' ')}." if blocking_value else None,
        f"Recommended action: {mismatch.recommended_action}" if mismatch.recommended_action else None,
        mismatch.next_step_target and f"Next step target: {mismatch.next_step_target}",
        "",
        "Values (read-only snapshot):",
        f"• Documented: {_format_value(mismatch.documented_value)}",
        f"• Observed: {_format_value(mismatch.observed_value)}",
        "",
        "Provenance:",
        f"• Mismatch signature: {mismatch.mismatch_signature}",
        mismatch.device_id is not None and f"• iliOS device #{mismatch.device_id}"
        + (f" ({mismatch.device_name})" if mismatch.device_name else ""),
        mismatch.external_device_id and f"• External device id: {mismatch.external_device_id}",
        "",
        "Created from the read-only Inventory Reconciliation view. Reconciliation itself "
        "changes nothing — this task only records the work to be done.",
    ]
    return "\n".join(line for line in lines if line)


def _resolve_asset_board(db: Session, site_id: int) -> Board:
    """Resolve the site's Asset task board (where inventory work belongs)."""
    board = (
        db.query(Board)
        .join(BoardRelatedEntity, BoardRelatedEntity.board_id == Board.id)
        .filter(
            BoardRelatedEntity.entity_type == BoardRelatedEntityTypeEnum.site,
            BoardRelatedEntity.entity_id == site_id,
            BoardRelatedEntity.extra_entity_type.is_(None),
            Board.module == BoardModuleEnum.asset,
            Board.is_active.is_(True),
        )
        .order_by(Board.id.asc())
        .first()
    )
    if board is None:
        logger.warning("No active Asset board for site %s; cannot create inventory task.", site_id)
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This project has no Asset task board, so an inventory task can't be created here.",
        )
    return board


def _site_board_ids(db: Session, site_id: int) -> list[int]:
    rows = (
        db.query(Board.id)
        .join(BoardRelatedEntity, BoardRelatedEntity.board_id == Board.id)
        .filter(
            BoardRelatedEntity.entity_type == BoardRelatedEntityTypeEnum.site,
            BoardRelatedEntity.entity_id == site_id,
        )
        .all()
    )
    return [row[0] for row in rows]


def _find_open_duplicate(db: Session, site_id: int, signature: str) -> Optional[Task]:
    """An OPEN (completed_at IS NULL) task on any of the site's boards that was
    generated from the same mismatch signature."""
    board_ids = _site_board_ids(db, site_id)
    if not board_ids:
        return None
    return (
        db.query(Task)
        .filter(
            Task.board_id.in_(board_ids),
            Task.source_kind == INVENTORY_SOURCE_KIND,
            Task.source_signature == signature,
            Task.completed_at.is_(None),
        )
        .order_by(Task.id.asc())
        .first()
    )


def _deep_link(site: Site, task_id: int) -> str:
    return f"/project-hub/companies/{site.company_id}/sites/{site.id}/tasks/{task_id}"


def create_task_from_inventory_mismatch(
    db: Session,
    site: Site,
    current_user: CurrentUserSchema,
    payload: InventoryMismatchTaskCreateSchema,
) -> InventoryMismatchTaskResponseSchema:
    """Create (or return the existing open) tracked task for one inventory gap."""
    # 1. Re-resolve the mismatch read-only; signature must still be present.
    reconciliation = build_site_inventory_reconciliation(db, site)
    mismatch = next(
        (m for m in reconciliation.mismatches if m.mismatch_signature == payload.mismatch_signature),
        None,
    )
    if mismatch is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "That reconciliation finding is no longer present. Refresh the reconciliation and try again.",
        )

    # 2. Only actionable mismatches may become tasks (server-side backstop).
    if not _is_actionable(mismatch):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This reconciliation finding is informational and has no actionable next step, so no task is created.",
        )

    # 3. Dedupe: an open task already tracking this gap wins (no second task).
    existing = _find_open_duplicate(db, site.id, payload.mismatch_signature)
    if existing is not None:
        logger.info(
            "Open inventory task #%s already tracks mismatch %s on site %s.",
            existing.id,
            payload.mismatch_signature,
            site.id,
        )
        return InventoryMismatchTaskResponseSchema(
            created=False,
            duplicate=True,
            task_id=existing.id,
            external_id=existing.external_id,
            board_id=existing.board_id,
            mismatch_signature=payload.mismatch_signature,
            message="An open task is already tracking this inventory gap.",
            deep_link=_deep_link(site, existing.id),
        )

    # 4. Resolve the Asset board + default (lowest-id) status.
    board = _resolve_asset_board(db, site.id)
    handler = TaskTrackerHandlerFactory(db).get_instance(board)
    status_ids = sorted(board.get_statuses_ids())
    if not status_ids:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The Asset task board has no statuses configured, so a task can't be created.",
        )
    default_status_id = status_ids[0]

    # 5. Resolve task fields, defaulting from the mismatch where the client omits.
    due_date = payload.due_date or (date.today() + timedelta(days=_DEFAULT_DUE_DATE_OFFSET_DAYS))
    priority = payload.priority or _default_priority(mismatch)
    name = (payload.name or _default_name(mismatch)).strip()[:_MAX_NAME_LENGTH]
    if not name:
        name = _default_name(mismatch)
    description = payload.description if payload.description is not None else _build_description(site, mismatch)

    # Link the device only when the mismatch names one that belongs to the site.
    affected_device_id: Optional[int] = None
    if mismatch.device_id is not None and mismatch.device_id in site.get_affected_devices_ids():
        affected_device_id = mismatch.device_id

    # 6. Reuse the standard task validations (assignee membership, due date).
    if payload.assignee_id is not None:
        handler.validate_task_assignee_id(payload)  # uses .assignee_id duck-typed
    handler.validate_task_due_date(_DueDateOnly(due_date))

    # 7. Persist with provenance. completed_at stays NULL (open).
    blocking_value = getattr(mismatch.blocking_level, "value", mismatch.blocking_level)
    category_value = getattr(mismatch.category, "value", mismatch.category)
    ack_value = getattr(mismatch.acknowledgement_policy, "value", mismatch.acknowledgement_policy)
    source_context = {
        "site_id": site.id,
        "company_id": site.company_id,
        "mismatch_signature": mismatch.mismatch_signature,
        "category": category_value,
        "blocking_level": blocking_value,
        "acknowledgement_policy": ack_value,
        "recommended_action": mismatch.recommended_action,
        "next_step_target": mismatch.next_step_target,
        "device_id": mismatch.device_id,
        "external_device_id": mismatch.external_device_id,
        "documented_value": mismatch.documented_value,
        "observed_value": mismatch.observed_value,
        # Provenance only — intentionally NOT part of the dedupe key.
        "reconciliation_generated_at": reconciliation.generated_at.isoformat()
        if reconciliation.generated_at
        else None,
    }

    task_crud = TaskCRUD(db)
    task_payload = {
        "name": name,
        "description": description,
        "priority": priority.value,
        "due_date": due_date,
        "assignee_id": payload.assignee_id,
        "status_id": default_status_id,
        "board_id": board.id,
        "creator_id": current_user.id,
        "affected_device_id": affected_device_id,
        "external_id": handler.generate_task_external_id(task_crud),
        "source_kind": INVENTORY_SOURCE_KIND,
        "source_signature": mismatch.mismatch_signature,
        "source_context": source_context,
    }
    try:
        task = task_crud.create_item(task_payload)
    except UniqueConstraintViolationError:
        logger.exception("Unique constraint violation creating inventory task on board %s.", board.id)
        raise HTTPException(status.HTTP_409_CONFLICT, TaskMessages.alert_task_already_exists)

    logger.info(
        "Created inventory task #%s on board %s for mismatch %s (site %s).",
        task.id,
        board.id,
        mismatch.mismatch_signature,
        site.id,
    )
    return InventoryMismatchTaskResponseSchema(
        created=True,
        duplicate=False,
        task_id=task.id,
        external_id=task.external_id,
        board_id=board.id,
        mismatch_signature=mismatch.mismatch_signature,
        message=TaskMessages.task_create_success,
        deep_link=_deep_link(site, task.id),
    )


class _DueDateOnly:
    """Tiny duck-typed shim so we can reuse ``validate_task_due_date`` (which only
    reads ``.due_date``) without constructing a full task payload schema."""

    def __init__(self, due_date: date) -> None:
        self.due_date = due_date
