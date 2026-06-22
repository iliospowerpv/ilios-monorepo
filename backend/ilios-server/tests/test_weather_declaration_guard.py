"""WS.1 — tests for the weather-declaration append-only governance layer.

Three concerns are covered independently:

1. The **DB trigger** (``enforce_weather_declaration_append_only``). The pytest
   harness builds the schema with ``Base.metadata.create_all`` (not migrations),
   so the ``weather_guard`` fixture applies the canonical guard SQL on the test
   engine and removes it afterwards. The trigger is exercised with raw SQL in
   isolated transactions so an expected ``RAISE EXCEPTION`` aborts only its own
   transaction.
2. The **ORM guard** (:func:`assert_governed_update_allowed`) — a pure mirror of
   the trigger over plain dicts.
3. The pure **verdict/policy** helpers in ``declaration_policy``.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db.weather_declaration_guard import (
    APPLY_GUARD_SQL,
    REMOVE_GUARD_SQL,
    WeatherDeclarationGuardError,
    assert_governed_update_allowed,
)
from app.models.weather import (
    WeatherCalibrationStatus,
    WeatherDeclarationBasis,
    WeatherDeclarationStatus,
    WeatherIrradiancePlane,
    WeatherTemperatureType,
)
from app.services.weather import declaration_policy as dp
from tests.conftest import engine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def weather_guard():
    """Install the append-only trigger on the test DB, then remove it.

    ``create_all`` does not create triggers, so the guard is applied here exactly
    as the migration applies it (same canonical SQL), then dropped on teardown so
    other test modules see unmodified behavior.
    """
    with engine.begin() as conn:
        for stmt in APPLY_GUARD_SQL:
            conn.execute(text(stmt))
    yield
    with engine.begin() as conn:
        for stmt in REMOVE_GUARD_SQL:
            conn.execute(text(stmt))


@pytest.fixture()
def mapping_factory(weather_guard, site_id):
    """Insert governed/legacy ``weather_device_mappings`` rows and clean them up.

    Returns a callable that inserts one row (raw SQL, committed in its own
    transaction) and returns its id. All inserted ids are deleted on teardown
    (DELETE is not constrained by the BEFORE UPDATE trigger).
    """
    created: list[int] = []

    def _make(
        *,
        metric: str = "irradiance_wm2",
        irradiance_plane: str = "poa",
        temperature_type: str = "unknown",
        calibration_status: str = "calibrated",
        declaration_status: str | None = "active",
        declaration_basis: str | None = "source_document",
        sensor_role: str | None = "poa_reference",
        needs_re_review: bool | None = False,
    ) -> int:
        params = {
            "site_id": site_id,
            "metric": metric,
            "irradiance_plane": irradiance_plane,
            "temperature_type": temperature_type,
            "calibration_status": calibration_status,
            "declaration_status": declaration_status,
            "declaration_basis": declaration_basis,
            "sensor_role": sensor_role,
            "needs_re_review": needs_re_review,
        }
        sql = text(
            """
            INSERT INTO weather_device_mappings
                (site_id, metric, irradiance_plane, temperature_type,
                 calibration_status, declaration_status, declaration_basis,
                 sensor_role, needs_re_review)
            VALUES
                (:site_id, :metric, :irradiance_plane, :temperature_type,
                 :calibration_status, :declaration_status, :declaration_basis,
                 :sensor_role, :needs_re_review)
            RETURNING id
            """
        )
        with engine.begin() as conn:
            new_id = conn.execute(sql, params).scalar_one()
        created.append(new_id)
        return new_id

    yield _make

    if created:
        with engine.begin() as conn:
            conn.execute(
                text("DELETE FROM weather_device_mappings WHERE id = ANY(:ids)"),
                {"ids": created},
            )


def _update(mapping_id: int, set_clause: str, params: dict | None = None) -> None:
    payload = {"id": mapping_id, **(params or {})}
    with engine.begin() as conn:
        conn.execute(
            text(f"UPDATE weather_device_mappings SET {set_clause} WHERE id = :id"),
            payload,
        )


def _status(mapping_id: int) -> str | None:
    with engine.connect() as conn:
        return conn.execute(
            text("SELECT declaration_status FROM weather_device_mappings WHERE id = :id"),
            {"id": mapping_id},
        ).scalar_one()


# ---------------------------------------------------------------------------
# 1. DB trigger
# ---------------------------------------------------------------------------
class TestDeclarationGuardTrigger:
    def test_insert_is_unconstrained(self, mapping_factory):
        """The trigger is BEFORE UPDATE only; inserting a governed row succeeds."""
        new_id = mapping_factory(declaration_status="active")
        assert isinstance(new_id, int)
        assert _status(new_id) == "active"

    @pytest.mark.parametrize(
        "set_clause",
        [
            "irradiance_plane = 'ghi'",
            "temperature_type = 'ambient'",
            "calibration_status = 'expired'",
            "declaration_basis = 'reviewer_assumption'",
            "metric = 'something_else'",
            "sensor_role = 'changed'",
            "reviewer_note = 'tampered'",
        ],
    )
    def test_protected_columns_are_immutable(self, mapping_factory, set_clause):
        new_id = mapping_factory(declaration_status="active")
        with pytest.raises(DBAPIError) as exc:
            _update(new_id, set_clause)
        assert "governance" in str(exc.value)

    def test_legal_transition_draft_to_active(self, mapping_factory):
        new_id = mapping_factory(declaration_status="draft")
        _update(new_id, "declaration_status = 'active', activated_at = now()")
        assert _status(new_id) == "active"

    def test_legal_transition_active_to_superseded(self, mapping_factory):
        target = mapping_factory(declaration_status="active")
        new_id = mapping_factory(declaration_status="active")
        _update(
            new_id,
            "declaration_status = 'superseded', superseded_by_mapping_id = :tid",
            {"tid": target},
        )
        assert _status(new_id) == "superseded"

    def test_flag_needs_re_review_false_to_true_allowed(self, mapping_factory):
        new_id = mapping_factory(declaration_status="active", needs_re_review=False)
        _update(new_id, "needs_re_review = true, re_review_reason = 'upstream changed'")
        with engine.connect() as conn:
            flag = conn.execute(
                text("SELECT needs_re_review FROM weather_device_mappings WHERE id = :id"),
                {"id": new_id},
            ).scalar_one()
        assert flag is True

    def test_clearing_needs_re_review_is_rejected(self, mapping_factory):
        new_id = mapping_factory(declaration_status="active", needs_re_review=True)
        with pytest.raises(DBAPIError) as exc:
            _update(new_id, "needs_re_review = false")
        assert "needs_re_review" in str(exc.value)

    @pytest.mark.parametrize(
        "from_status,to_status",
        [
            ("active", "draft"),
            ("draft", "superseded"),
            ("superseded", "active"),
        ],
    )
    def test_illegal_status_transitions_rejected(
        self, mapping_factory, from_status, to_status
    ):
        new_id = mapping_factory(declaration_status=from_status)
        with pytest.raises(DBAPIError) as exc:
            _update(new_id, f"declaration_status = '{to_status}'")
        assert "transition" in str(exc.value)

    def test_set_once_activated_at_cannot_change(self, mapping_factory):
        new_id = mapping_factory(declaration_status="draft")
        _update(new_id, "declaration_status = 'active', activated_at = now()")
        with pytest.raises(DBAPIError) as exc:
            _update(new_id, "activated_at = now() + interval '1 day'")
        assert "set-once" in str(exc.value)

    def test_site_id_is_immutable_on_governed_row(self, mapping_factory):
        """A governed row's site scope cannot be re-parented in place."""
        new_id = mapping_factory(declaration_status="active")
        with pytest.raises(DBAPIError) as exc:
            _update(new_id, "site_id = site_id + 100000")
        assert "governance" in str(exc.value)

    def test_created_at_is_immutable_on_governed_row(self, mapping_factory):
        new_id = mapping_factory(declaration_status="active")
        with pytest.raises(DBAPIError) as exc:
            _update(new_id, "created_at = now() + interval '1 day'")
        assert "governance" in str(exc.value)

    def test_active_to_superseded_requires_backlink(self, mapping_factory):
        """Supersession must name the replacing declaration at the DB layer."""
        new_id = mapping_factory(declaration_status="active")
        with pytest.raises(DBAPIError) as exc:
            _update(new_id, "declaration_status = 'superseded'")
        assert "governance" in str(exc.value)
        assert _status(new_id) == "active"

    def test_activation_fields_only_during_activation(self, mapping_factory):
        """Activation fields cannot be set on an active row without the transition."""
        new_id = mapping_factory(declaration_status="active")
        with pytest.raises(DBAPIError) as exc:
            _update(new_id, "activated_at = now()")
        assert "governance" in str(exc.value)

    def test_supersede_backlink_only_during_supersession(self, mapping_factory):
        """The backlink cannot be set without the active->superseded transition."""
        target = mapping_factory(declaration_status="active")
        new_id = mapping_factory(declaration_status="active")
        with pytest.raises(DBAPIError) as exc:
            _update(
                new_id,
                "superseded_by_mapping_id = :tid",
                {"tid": target},
            )
        assert "governance" in str(exc.value)

    def test_stale_flag_on_draft_is_rejected(self, mapping_factory):
        new_id = mapping_factory(declaration_status="draft")
        with pytest.raises(DBAPIError) as exc:
            _update(new_id, "needs_re_review = true")
        assert "governance" in str(exc.value)

    def test_re_review_reason_change_without_flag_rejected(self, mapping_factory):
        new_id = mapping_factory(declaration_status="active", needs_re_review=False)
        with pytest.raises(DBAPIError) as exc:
            _update(new_id, "re_review_reason = 'tampered'")
        assert "governance" in str(exc.value)

    def test_legacy_null_status_rows_are_exempt(self, mapping_factory):
        """A NULL-status (ungoverned) row keeps its historical free-edit behavior."""
        new_id = mapping_factory(declaration_status=None, declaration_basis=None)
        # An edit that would be rejected on a governed row is allowed here.
        _update(new_id, "irradiance_plane = 'ghi', calibration_status = 'expired'")
        with engine.connect() as conn:
            plane = conn.execute(
                text("SELECT irradiance_plane FROM weather_device_mappings WHERE id = :id"),
                {"id": new_id},
            ).scalar_one()
        assert plane == "ghi"


# ---------------------------------------------------------------------------
# 2. ORM guard (pure)
# ---------------------------------------------------------------------------
class TestAssertGovernedUpdateAllowed:
    def _governed(self, **overrides):
        base = {
            "site_id": 1,
            "declaration_status": "active",
            "declaration_basis": "source_document",
            "irradiance_plane": "poa",
            "temperature_type": "unknown",
            "calibration_status": "calibrated",
            "sensor_role": "poa_reference",
            "needs_re_review": False,
            "re_review_reason": None,
            "activated_by": None,
            "activated_at": None,
            "superseded_by_mapping_id": None,
            "eligibility_snapshot_json": None,
        }
        base.update(overrides)
        return base

    def test_legacy_row_is_exempt(self):
        old = self._governed(declaration_status=None)
        new = self._governed(declaration_status=None, irradiance_plane="ghi")
        # Should NOT raise even though a protected column changed.
        assert_governed_update_allowed(old, new) is None

    def test_protected_column_change_raises(self):
        old = self._governed()
        new = self._governed(irradiance_plane="ghi")
        with pytest.raises(WeatherDeclarationGuardError):
            assert_governed_update_allowed(old, new)

    def test_illegal_status_transition_raises(self):
        old = self._governed(declaration_status="active")
        new = self._governed(declaration_status="draft")
        with pytest.raises(WeatherDeclarationGuardError):
            assert_governed_update_allowed(old, new)

    def test_legal_transition_allowed(self):
        old = self._governed(declaration_status="draft")
        new = self._governed(declaration_status="active", activated_by=7)
        assert_governed_update_allowed(old, new) is None

    def test_clearing_needs_re_review_raises(self):
        old = self._governed(needs_re_review=True)
        new = self._governed(needs_re_review=False)
        with pytest.raises(WeatherDeclarationGuardError):
            assert_governed_update_allowed(old, new)

    def test_set_once_change_raises(self):
        old = self._governed(activated_by=7)
        new = self._governed(activated_by=9)
        with pytest.raises(WeatherDeclarationGuardError):
            assert_governed_update_allowed(old, new)

    def test_activation_fields_initialized_during_activation_allowed(self):
        """Activation fields may be initialized in the draft->active update."""
        old = self._governed(declaration_status="draft")
        new = self._governed(
            declaration_status="active",
            activated_by=7,
            activated_at="2026-01-01T00:00:00",
            eligibility_snapshot_json={"ok": True},
        )
        assert assert_governed_update_allowed(old, new) is None

    def test_activation_field_outside_transition_raises(self):
        """Setting an activation field on an already-active row (no transition)."""
        old = self._governed(declaration_status="active", activated_by=None)
        new = self._governed(declaration_status="active", activated_by=7)
        with pytest.raises(WeatherDeclarationGuardError):
            assert_governed_update_allowed(old, new)

    def test_site_id_change_raises(self):
        old = self._governed(site_id=1)
        new = self._governed(site_id=2)
        with pytest.raises(WeatherDeclarationGuardError):
            assert_governed_update_allowed(old, new)

    def test_supersede_without_backlink_raises(self):
        old = self._governed(declaration_status="active")
        new = self._governed(declaration_status="superseded")
        with pytest.raises(WeatherDeclarationGuardError):
            assert_governed_update_allowed(old, new)

    def test_supersede_with_backlink_allowed(self):
        old = self._governed(declaration_status="active")
        new = self._governed(
            declaration_status="superseded", superseded_by_mapping_id=5
        )
        assert assert_governed_update_allowed(old, new) is None

    def test_supersede_backlink_outside_transition_raises(self):
        """The supersession backlink cannot be set without the transition."""
        old = self._governed(declaration_status="active")
        new = self._governed(
            declaration_status="active", superseded_by_mapping_id=5
        )
        with pytest.raises(WeatherDeclarationGuardError):
            assert_governed_update_allowed(old, new)

    def test_stale_flag_on_draft_raises(self):
        old = self._governed(declaration_status="draft", needs_re_review=False)
        new = self._governed(declaration_status="draft", needs_re_review=True)
        with pytest.raises(WeatherDeclarationGuardError):
            assert_governed_update_allowed(old, new)

    def test_flag_stale_with_reason_allowed(self):
        old = self._governed(needs_re_review=False, re_review_reason=None)
        new = self._governed(needs_re_review=True, re_review_reason="upstream changed")
        assert assert_governed_update_allowed(old, new) is None

    def test_re_review_reason_change_without_flag_raises(self):
        old = self._governed(needs_re_review=False, re_review_reason=None)
        new = self._governed(needs_re_review=False, re_review_reason="tampered")
        with pytest.raises(WeatherDeclarationGuardError):
            assert_governed_update_allowed(old, new)


# ---------------------------------------------------------------------------
# 3. Verdict / policy matrix (pure)
# ---------------------------------------------------------------------------
class TestDeclarationVerdict:
    def _eligible_kwargs(self, **overrides):
        base = dict(
            declaration_status=WeatherDeclarationStatus.active,
            declaration_basis=WeatherDeclarationBasis.source_document,
            irradiance_plane=WeatherIrradiancePlane.poa,
            temperature_type=WeatherTemperatureType.unknown,
            calibration_status=WeatherCalibrationStatus.calibrated,
            calibrated_at="2026-01-01T00:00:00",
            calibration_reference="cert-123",
            sensor_role="poa_reference",
            needs_re_review=False,
        )
        base.update(overrides)
        return base

    def test_no_declaration(self):
        v = dp.verdict_for_no_declaration()
        assert v.expected_model_eligible is False
        assert v.declaration_state == dp.STATE_SOURCE_EXISTS_SEMANTICS_UNKNOWN
        assert dp.REASON_MISSING_DECLARATION in v.reason_codes

    def test_none_mapping(self):
        v = dp.evaluate_mapping(None)
        assert v.declaration_state == dp.STATE_SOURCE_EXISTS_SEMANTICS_UNKNOWN

    def test_draft_never_eligible(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(
            declaration_status=WeatherDeclarationStatus.draft
        ))
        assert v.expected_model_eligible is False
        assert v.declaration_state == dp.STATE_DECLARATION_DRAFT
        assert dp.REASON_DRAFT_NOT_ACTIVATED in v.reason_codes

    def test_superseded_never_eligible(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(
            declaration_status=WeatherDeclarationStatus.superseded
        ))
        assert v.expected_model_eligible is False
        assert dp.REASON_SUPERSEDED in v.reason_codes

    def test_active_needs_re_review_is_stale(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(needs_re_review=True))
        assert v.expected_model_eligible is False
        assert v.declaration_state == dp.STATE_DECLARATION_STALE_NEEDS_RE_REVIEW
        assert dp.REASON_STALE_NEEDS_RE_REVIEW in v.reason_codes

    def test_poa_calibrated_source_document_is_eligible(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs())
        assert v.expected_model_eligible is True
        assert v.declaration_state == dp.STATE_DECLARED_ELIGIBLE_INTEGRATION_PENDING
        assert v.layer1_message == dp.LAYER1_ELIGIBLE_MESSAGE
        assert v.required_action is None

    def test_reviewer_assumption_never_eligible_even_with_poa_calibrated(self):
        """Basis gate: a non-qualifying basis can never be eligible."""
        v = dp.evaluate_declaration(**self._eligible_kwargs(
            declaration_basis=WeatherDeclarationBasis.reviewer_assumption
        ))
        assert v.expected_model_eligible is False
        assert dp.REASON_BASIS_NOT_QUALIFYING in v.reason_codes

    def test_reviewer_source_note_never_eligible(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(
            declaration_basis=WeatherDeclarationBasis.reviewer_source_note
        ))
        assert v.expected_model_eligible is False
        assert dp.REASON_BASIS_NOT_QUALIFYING in v.reason_codes

    def test_poa_missing_calibration_cert_not_eligible(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(
            calibrated_at=None, calibration_reference=None
        ))
        assert v.expected_model_eligible is False
        assert dp.REASON_CALIBRATION_REQUIRED_MISSING in v.reason_codes

    def test_poa_expired_calibration_validity_unknown(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(
            calibration_status=WeatherCalibrationStatus.expired
        ))
        assert v.expected_model_eligible is False
        assert dp.REASON_CALIBRATION_VALIDITY_UNKNOWN in v.reason_codes

    def test_cell_temperature_calibrated_is_eligible(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(
            irradiance_plane=WeatherIrradiancePlane.unknown,
            temperature_type=WeatherTemperatureType.cell,
            sensor_role="cell_temp",
        ))
        assert v.expected_model_eligible is True
        assert v.physics_usable_temperature is True

    def test_modeled_cell_needs_no_calibration(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(
            irradiance_plane=WeatherIrradiancePlane.unknown,
            temperature_type=WeatherTemperatureType.modeled_cell,
            calibration_status=WeatherCalibrationStatus.unknown,
            calibrated_at=None,
            calibration_reference=None,
            sensor_role="modeled",
        ))
        assert v.expected_model_eligible is True
        assert v.calibration_ok is True

    def test_ghi_irradiance_not_poa(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(
            irradiance_plane=WeatherIrradiancePlane.ghi
        ))
        assert v.expected_model_eligible is False
        assert dp.REASON_IRRADIANCE_NOT_POA in v.reason_codes
        assert dp.REASON_NO_USABLE_MEASUREMENT not in v.reason_codes

    def test_ambient_temperature_not_cell_usable(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(
            irradiance_plane=WeatherIrradiancePlane.unknown,
            temperature_type=WeatherTemperatureType.ambient,
            sensor_role="ambient_temp",
        ))
        assert v.expected_model_eligible is False
        assert dp.REASON_TEMPERATURE_NOT_CELL_USABLE in v.reason_codes

    def test_nothing_declared_no_usable_measurement(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(
            irradiance_plane=WeatherIrradiancePlane.unknown,
            temperature_type=WeatherTemperatureType.unknown,
        ))
        assert v.expected_model_eligible is False
        assert dp.REASON_NO_USABLE_MEASUREMENT in v.reason_codes

    def test_sensor_role_missing(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(sensor_role=None))
        assert v.expected_model_eligible is False
        assert dp.REASON_SENSOR_ROLE_MISSING in v.reason_codes

    def test_window_coverage_gap_fails_eligibility(self):
        v = dp.evaluate_declaration(
            **self._eligible_kwargs(), window_coverage_ok=False
        )
        assert v.expected_model_eligible is False
        assert dp.REASON_EFFECTIVE_WINDOW_GAP in v.reason_codes

    def test_window_coverage_none_does_not_fail(self):
        v = dp.evaluate_declaration(**self._eligible_kwargs(), window_coverage_ok=None)
        assert v.expected_model_eligible is True

    def test_physics_usable_helpers(self):
        assert dp.physics_usable_irradiance(WeatherIrradiancePlane.poa) is True
        assert dp.physics_usable_irradiance(WeatherIrradiancePlane.ghi) is False
        assert dp.physics_usable_irradiance(WeatherIrradiancePlane.unknown) is False
        assert dp.physics_usable_temperature(WeatherTemperatureType.cell) is True
        assert dp.physics_usable_temperature(WeatherTemperatureType.module) is True
        assert dp.physics_usable_temperature(WeatherTemperatureType.modeled_cell) is True
        assert dp.physics_usable_temperature(WeatherTemperatureType.ambient) is False

    def test_calibration_required_matrix(self):
        assert dp.calibration_required(
            plane=WeatherIrradiancePlane.poa,
            temperature_type=WeatherTemperatureType.unknown,
        ) is True
        assert dp.calibration_required(
            plane=WeatherIrradiancePlane.unknown,
            temperature_type=WeatherTemperatureType.cell,
        ) is True
        assert dp.calibration_required(
            plane=WeatherIrradiancePlane.unknown,
            temperature_type=WeatherTemperatureType.module,
        ) is True
        assert dp.calibration_required(
            plane=WeatherIrradiancePlane.unknown,
            temperature_type=WeatherTemperatureType.modeled_cell,
        ) is False
