"""Create-a-task-from-an-inventory-gap (Task #60) — the single write seam.

The inventory reconciliation read path is strictly read-only; this is the ONLY
place a reconciliation finding turns into a tracked task, and only on an explicit
``mismatch_signature`` request (never auto-created). These tests pin the
load-bearing contracts of
``app.services.telemetry.inventory_mismatch_task_service``:

1. **Actionable-only.** A purely informational finding (recommended action present
   but ``blocking_level``/``acknowledgement_policy`` informational) is rejected
   with 422; an unknown/stale signature is rejected with 404.
2. **Open-only dedupe.** A second create for the same (site, signature) while an
   OPEN task exists returns the existing task (``created=False``) and writes no new
   row; once the first task is closed (``completed_at`` set), a fresh create
   succeeds again — a re-appearing gap stays trackable.
3. **Read-side immutability.** Creating a task never mutates any reconciliation
   *source* table (devices, mappings, project_facts, external sites/devices, sync
   jobs, weather mappings, expected baselines); only ``tasks`` grows.
4. **Provenance + linkage.** The created task lands on the site's Asset board, is
   open (``completed_at IS NULL``), carries ``source_kind``/``source_signature``,
   and stores a provenance ``source_context`` snapshot.
5. **Endpoint auth.** A user with no access to the site is rejected with 403.

It reuses the validated Site-4-shaped scenario builder from the reconciliation
suite (which yields, among others, an actionable ``telemetry_freshness`` finding
and an informational ``undocumented_telemetry_device`` finding). DB-backed; no
``pytest-mock``.
"""
from __future__ import annotations

import copy
import itertools

import pytest
from fastapi import HTTPException

from app.crud.user import UserCRUD
from app.helpers.task_tracker.board_defaults_helper import create_default_board
from app.models.board import Board, BoardModuleEnum, BoardRelatedEntityTypeEnum
from app.models.task import Task, TaskPriorityEnum
from app.schema.task import InventoryMismatchTaskCreateSchema
from app.schema.user import CurrentUserSchema
from app.services.telemetry import inventory_mismatch_task_service as task_svc
from app.services.telemetry.inventory_mismatch_task_service import INVENTORY_SOURCE_KIND

# Reuse the validated reconciliation scenario builder + helpers verbatim.
from tests.unit.telemetry.device_inventory_reconciliation_test import (
    _FINGERPRINT_MODELS,
    _build_site4_shaped,
    _fingerprint,
    _site,
)

_SEQ = itertools.count(1)

# Signatures emitted by the Site-4-shaped builder (see that suite's docstring).
_ACTIONABLE_SIG = "telemetry_freshness:site:discovery_stale"  # lowers_confidence
_INFORMATIONAL_SIG = "undocumented_telemetry_device:other:external:UPS-EXT"
_UNKNOWN_SIG = "no_such_finding:does:not:exist"


# ---------------------------------------------------------------------------
# Self-contained company + per-test site (mirrors the reconciliation suite)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def company_id(db_session):
    from app.crud.company import CompanyCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.SETUP_COMPANIES[0])
    suffix = next(_SEQ)
    payload["name"] = f"{payload['name']} InvTaskCo-{suffix}"
    if payload.get("email"):
        local, _, domain = payload["email"].partition("@")
        payload["email"] = f"{local}+invtask{suffix}@{domain or 'example.com'}"
    return CompanyCRUD(db_session).create_item(payload).id


@pytest.fixture()
def site_id(db_session, company_id) -> int:
    from app.crud.site import SiteCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.TEST_SITE_BODY)
    payload["company_id"] = company_id
    payload["name"] = f"{payload['name']} InvTask-{next(_SEQ)}"
    return SiteCRUD(db_session).create_item(payload).id


@pytest.fixture()
def creator(db_session) -> CurrentUserSchema:
    """A real persisted user so ``tasks.creator_id`` satisfies its FK."""
    from tests.unit import samples

    payload = copy.deepcopy(samples.BASE_USER_OBJECT)
    suffix = next(_SEQ)
    payload["email"] = f"invtask.creator.{suffix}@iliostest.com"
    payload["is_registered"] = True
    user = UserCRUD(db_session).create_item(payload)
    return CurrentUserSchema(id=user.id, email=user.email)


@pytest.fixture()
def asset_board(db_session, site_id) -> Board:
    """The site's default (Asset-module) task board — where inventory work lands."""
    return create_default_board(site_id, BoardRelatedEntityTypeEnum.site, db_session)


def _payload(signature: str, **extra) -> InventoryMismatchTaskCreateSchema:
    return InventoryMismatchTaskCreateSchema(mismatch_signature=signature, **extra)


def _open_inventory_tasks(db, board_id: int, signature: str) -> list[Task]:
    return (
        db.query(Task)
        .filter(
            Task.board_id == board_id,
            Task.source_kind == INVENTORY_SOURCE_KIND,
            Task.source_signature == signature,
        )
        .order_by(Task.id.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Happy path — provenance + linkage
# ---------------------------------------------------------------------------
class TestCreate:
    def test_actionable_mismatch_creates_open_task_on_asset_board(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)

        result = task_svc.create_task_from_inventory_mismatch(
            db_session,
            _site(db_session, site_id),
            creator,
            _payload(_ACTIONABLE_SIG),
        )

        assert result.created is True
        assert result.duplicate is False
        assert result.board_id == asset_board.id
        assert result.mismatch_signature == _ACTIONABLE_SIG
        assert result.deep_link and str(site_id) in result.deep_link

        task = db_session.query(Task).filter(Task.id == result.task_id).one()
        assert task.board_id == asset_board.id
        assert asset_board.module == BoardModuleEnum.asset
        assert task.completed_at is None  # open
        assert task.creator_id == creator.id
        assert task.source_kind == INVENTORY_SOURCE_KIND
        assert task.source_signature == _ACTIONABLE_SIG
        # lowers_confidence → medium priority default.
        assert task.priority == TaskPriorityEnum.medium.value
        # Provenance snapshot is stored and self-describing.
        assert task.source_context["mismatch_signature"] == _ACTIONABLE_SIG
        assert task.source_context["site_id"] == site_id
        assert task.source_context["recommended_action"]
        # Recommended action + signature are surfaced in the description.
        assert _ACTIONABLE_SIG in task.description

    def test_client_overrides_are_respected(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)

        result = task_svc.create_task_from_inventory_mismatch(
            db_session,
            _site(db_session, site_id),
            creator,
            _payload(
                _ACTIONABLE_SIG,
                name="Custom inventory follow-up",
                priority=TaskPriorityEnum.high,
                description="Investigate stale discovery.",
            ),
        )

        task = db_session.query(Task).filter(Task.id == result.task_id).one()
        assert task.name == "Custom inventory follow-up"
        assert task.priority == TaskPriorityEnum.high.value
        assert task.description == "Investigate stale discovery."


# ---------------------------------------------------------------------------
# Rejections — unknown signature (404) + informational finding (422)
# ---------------------------------------------------------------------------
class TestRejections:
    def test_unknown_signature_404(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)

        with pytest.raises(HTTPException) as exc:
            task_svc.create_task_from_inventory_mismatch(
                db_session,
                _site(db_session, site_id),
                creator,
                _payload(_UNKNOWN_SIG),
            )
        assert exc.value.status_code == 404
        assert _open_inventory_tasks(db_session, asset_board.id, _UNKNOWN_SIG) == []

    def test_informational_mismatch_422(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)

        with pytest.raises(HTTPException) as exc:
            task_svc.create_task_from_inventory_mismatch(
                db_session,
                _site(db_session, site_id),
                creator,
                _payload(_INFORMATIONAL_SIG),
            )
        assert exc.value.status_code == 422
        assert _open_inventory_tasks(db_session, asset_board.id, _INFORMATIONAL_SIG) == []


# ---------------------------------------------------------------------------
# Dedupe — open-only
# ---------------------------------------------------------------------------
class TestOpenOnlyDedupe:
    def test_second_create_returns_existing_open_task(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)
        site = _site(db_session, site_id)

        first = task_svc.create_task_from_inventory_mismatch(
            db_session, site, creator, _payload(_ACTIONABLE_SIG)
        )
        second = task_svc.create_task_from_inventory_mismatch(
            db_session, _site(db_session, site_id), creator, _payload(_ACTIONABLE_SIG)
        )

        assert first.created is True
        assert second.created is False
        assert second.duplicate is True
        assert second.task_id == first.task_id
        assert len(_open_inventory_tasks(db_session, asset_board.id, _ACTIONABLE_SIG)) == 1

    def test_create_again_after_close(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)

        first = task_svc.create_task_from_inventory_mismatch(
            db_session, _site(db_session, site_id), creator, _payload(_ACTIONABLE_SIG)
        )
        # Close the first task — a resolved gap must become trackable again.
        from datetime import datetime

        closed = db_session.query(Task).filter(Task.id == first.task_id).one()
        closed.completed_at = datetime.utcnow()
        db_session.commit()

        second = task_svc.create_task_from_inventory_mismatch(
            db_session, _site(db_session, site_id), creator, _payload(_ACTIONABLE_SIG)
        )

        assert second.created is True
        assert second.duplicate is False
        assert second.task_id != first.task_id
        rows = _open_inventory_tasks(db_session, asset_board.id, _ACTIONABLE_SIG)
        assert len(rows) == 2  # one closed + one fresh open


# ---------------------------------------------------------------------------
# Read-side immutability — source tables never change
# ---------------------------------------------------------------------------
class TestReadSideImmutability:
    def test_create_does_not_mutate_reconciliation_sources(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)

        before = _fingerprint(db_session)  # the recon source tables only
        result = task_svc.create_task_from_inventory_mismatch(
            db_session, _site(db_session, site_id), creator, _payload(_ACTIONABLE_SIG)
        )
        after = _fingerprint(db_session)

        assert result.created is True
        # Not one reconciliation-source row changed (Task is NOT in the set).
        assert "tasks" not in {m.__tablename__ for m in _FINGERPRINT_MODELS}
        assert before == after


# ---------------------------------------------------------------------------
# Endpoint authorization
# ---------------------------------------------------------------------------
class TestEndpointAuth:
    def test_post_without_site_access_403(
        self, client, company_id, site_id, non_system_user_auth_header
    ):
        response = client.post(
            f"api/telemetry/v2/sites/{site_id}/inventory-reconciliation/tasks",
            json={"mismatch_signature": _ACTIONABLE_SIG},
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_tracked_without_site_access_403(
        self, client, company_id, site_id, non_system_user_auth_header
    ):
        response = client.get(
            f"api/telemetry/v2/sites/{site_id}/inventory-reconciliation/tracked-tasks",
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Tracked-task companion lookup (Task #83) — read-only "Tracked" indicator
# ---------------------------------------------------------------------------
class TestTrackedTasks:
    """``list_tracked_inventory_tasks`` is the read-only companion to creation.

    It backs the "Tracked" vs "Create task" affordance: a row is "Tracked" iff an
    OPEN task carries its signature. These pin the load-bearing contracts —
    open-only, dedupe-collapsed, read-only, and single-query (no N+1).
    """

    def test_returns_open_task_for_created_signature(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)
        created = task_svc.create_task_from_inventory_mismatch(
            db_session, _site(db_session, site_id), creator, _payload(_ACTIONABLE_SIG)
        )

        result = task_svc.list_tracked_inventory_tasks(db_session, _site(db_session, site_id))

        by_sig = {t.mismatch_signature: t for t in result.tracked}
        assert _ACTIONABLE_SIG in by_sig
        tracked = by_sig[_ACTIONABLE_SIG]
        assert tracked.is_tracked is True
        assert tracked.task_id == created.task_id
        assert tracked.task_link and str(site_id) in tracked.task_link

    def test_empty_when_no_tracking_tasks(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)

        result = task_svc.list_tracked_inventory_tasks(db_session, _site(db_session, site_id))

        assert result.tracked == []

    def test_closed_task_not_tracked(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)
        created = task_svc.create_task_from_inventory_mismatch(
            db_session, _site(db_session, site_id), creator, _payload(_ACTIONABLE_SIG)
        )
        # Closing the only tracking task must drop the signature from the result,
        # so a resolved gap re-offers "Create task" (never a stale "Tracked").
        from datetime import datetime

        closed = db_session.query(Task).filter(Task.id == created.task_id).one()
        closed.completed_at = datetime.utcnow()
        db_session.commit()

        result = task_svc.list_tracked_inventory_tasks(db_session, _site(db_session, site_id))

        assert all(t.mismatch_signature != _ACTIONABLE_SIG for t in result.tracked)

    def test_dedupes_to_lowest_id_when_duplicate_open_tasks(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)
        first = task_svc.create_task_from_inventory_mismatch(
            db_session, _site(db_session, site_id), creator, _payload(_ACTIONABLE_SIG)
        )
        # Defensive: force a second OPEN row with the same signature (bypassing the
        # create-time dedupe) and assert the list collapses to the lowest id.
        dup = Task(
            name="dup tracking task",
            board_id=asset_board.id,
            creator_id=creator.id,
            source_kind=INVENTORY_SOURCE_KIND,
            source_signature=_ACTIONABLE_SIG,
        )
        db_session.add(dup)
        db_session.commit()

        result = task_svc.list_tracked_inventory_tasks(db_session, _site(db_session, site_id))

        rows = [t for t in result.tracked if t.mismatch_signature == _ACTIONABLE_SIG]
        assert len(rows) == 1
        assert rows[0].task_id == first.task_id

    def test_listing_does_not_mutate_sources(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)
        task_svc.create_task_from_inventory_mismatch(
            db_session, _site(db_session, site_id), creator, _payload(_ACTIONABLE_SIG)
        )

        before = _fingerprint(db_session)
        task_svc.list_tracked_inventory_tasks(db_session, _site(db_session, site_id))
        after = _fingerprint(db_session)

        assert before == after

    def test_single_query_no_n_plus_one(
        self, db_session, company_id, site_id, creator, asset_board
    ):
        _build_site4_shaped(db_session, company_id, site_id)
        # Several open tracking tasks across distinct signatures — reading each
        # task's status must NOT fan out into a per-row query.
        for sig in (_ACTIONABLE_SIG,):
            task_svc.create_task_from_inventory_mismatch(
                db_session, _site(db_session, site_id), creator, _payload(sig)
            )
        for i in range(3):
            db_session.add(
                Task(
                    name=f"extra tracking {i}",
                    board_id=asset_board.id,
                    creator_id=creator.id,
                    source_kind=INVENTORY_SOURCE_KIND,
                    source_signature=f"synthetic_gap:site:extra:{i}",
                )
            )
        db_session.commit()

        statements: list[str] = []
        from sqlalchemy import event

        engine = db_session.get_bind()

        def _before_cursor(conn, cursor, statement, parameters, context, executemany):
            if statement.lstrip().upper().startswith("SELECT"):
                statements.append(statement)

        event.listen(engine, "before_cursor_execute", _before_cursor)
        try:
            result = task_svc.list_tracked_inventory_tasks(db_session, _site(db_session, site_id))
        finally:
            event.remove(engine, "before_cursor_execute", _before_cursor)

        # board-ids resolution + the single tasks+status query. The eager
        # joinedload means status reads add NO extra SELECTs regardless of row count.
        assert len(result.tracked) >= 4
        task_selects = [s for s in statements if "FROM tasks" in s or "FROM task" in s]
        assert len(task_selects) == 1, statements
