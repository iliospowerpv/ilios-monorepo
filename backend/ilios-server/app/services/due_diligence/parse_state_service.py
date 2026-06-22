"""Data Room Parse-State Service (Phase 1).

Computes an honest, read-only summary of where a single file *version* sits in
the parse -> review -> accept/override -> promote lifecycle, so the Data Room can
stop rendering silently-empty documents.

This service is strictly READ-ONLY: it performs no commits, flushes, writes, or
object mutations intended for persistence. It never parses, accepts, overrides,
promotes, classifies, changes a document type, or alters baselines/facts. It only
reads existing parse runs, version-scoped document keys, promoted project facts,
and the extraction registry, and returns a `ParseStateSummary`.

Summary precedence (most-advanced durable state wins):
    promoted
    > accepted_or_overridden
    > parsed_awaiting_review
    > parsed_no_usable_fields
    > parse_failed
    > parsing_in_progress
    > not_yet_parsed

Durable advanced state is never regressed by a newer in-flight reprocess: when a
completed run already produced reviewable/accepted/promoted data and a *newer*
run is queued/processing, the durable state is kept and
``active_reprocess_in_progress`` is set instead of dropping back to
``parsing_in_progress``.
"""

import logging
from typing import NamedTuple, Optional

from sqlalchemy.orm import Session

from app.crud.ai_parsing_result import AIParsingResultCRUD
from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.models.document import DocumentKey
from app.models.file import File as FileModel
from app.models.file import FileParsingStatuses
from app.models.project_facts import FactStatus, ProjectFact
from app.schema.file import (
    NoUsableFieldsReason,
    ParseNextAction,
    ParseState,
    ParseStateFileVersionSchema,
    ParseStateLatestRunSchema,
    ParseStateSummary,
    SelectedDocumentTypeSchema,
)
from app.static.default_site_documents_enum import SiteDocumentsEnum

logger = logging.getLogger(__name__)

# The 10-field generic "contractual" stub schema shared by ~201 document types.
# Detection is by exact canonical field-name set equality so it survives display
# label changes and requires no migration or marker column. Sourced from the
# active schema versions of the equipment types (DB-verified).
GENERIC_CONTRACTUAL_FIELD_SET = frozenset(
    {
        "counterparties",
        "document_date",
        "document_title",
        "effective_date",
        "expiration_or_termination_date",
        "governing_law_or_jurisdiction",
        "key_amounts_or_fees",
        "key_obligations",
        "summary",
        "term_or_duration",
    }
)

# Equipment datasheet document types. This set ONLY governs the
# "no equipment-specific schema yet" messaging (Phase 2 will add real schemas);
# it never widens can_drive_expected or any health/readiness/expected math.
EQUIPMENT_DOCUMENT_TYPES = frozenset(
    {
        SiteDocumentsEnum.module_specs,
        SiteDocumentsEnum.inverter_specs,
        SiteDocumentsEnum.transformer_specs,
        SiteDocumentsEnum.storage_specs,
        SiteDocumentsEnum.battery_specs,
        SiteDocumentsEnum.racking_specs,
    }
)

FAILURE_STATUSES = frozenset(
    {
        FileParsingStatuses.processing_failed,
        FileParsingStatuses.processing_timeout,
        FileParsingStatuses.processing_start_failed,
        FileParsingStatuses.unprocessable_file,
    }
)

IN_PROGRESS_STATUSES = frozenset(
    {
        FileParsingStatuses.queued,
        FileParsingStatuses.processing,
    }
)

ACCEPTED_KEY_STATUSES = ("accepted", "overridden")


def _extract_parsed_field_values(run) -> dict:
    """Return ``{field_key: value}`` of non-empty parsed values from a completed
    run, supporting both the new ``parsed_result.fields[]`` format and the legacy
    ``result[]`` list. Read-only; never mutates the run."""
    values: dict = {}
    if run is None:
        return values

    parsed = run.parsed_result
    if parsed and isinstance(parsed, dict):
        for field in parsed.get("fields", []) or []:
            if not isinstance(field, dict):
                continue
            key = field.get("field_key")
            val = field.get("value")
            if key and val not in (None, ""):
                values[key] = val
        if values:
            return values

    legacy = run.result
    if legacy and isinstance(legacy, list):
        for item in legacy:
            if not isinstance(item, dict):
                continue
            key = item.get("key_item")
            val = item.get("value")
            if key and val not in (None, ""):
                values[key] = val
    return values


def _classify_no_usable_reason(
    schema_field_names: set, parsed_values: dict, is_generic_stub: bool
) -> NoUsableFieldsReason:
    """Pick the most accurate reason a completed parse yielded nothing reviewable."""
    if not schema_field_names:
        return NoUsableFieldsReason.no_schema_fields
    if not parsed_values:
        return NoUsableFieldsReason.no_fields_found
    # Values were extracted but none mapped to the active schema's fields.
    if is_generic_stub:
        return NoUsableFieldsReason.generic_contractual_schema
    return NoUsableFieldsReason.fields_did_not_map


def _next_action(
    parse_state: ParseState, is_equipment_type: bool, is_generic_stub: bool
) -> ParseNextAction:
    if parse_state == ParseState.not_yet_parsed:
        return ParseNextAction.parse_document
    if parse_state == ParseState.parsing_in_progress:
        return ParseNextAction.wait_for_parse
    if parse_state == ParseState.parse_failed:
        return ParseNextAction.retry_parse
    if parse_state == ParseState.parsed_no_usable_fields:
        if is_equipment_type and is_generic_stub:
            return ParseNextAction.awaiting_equipment_schema
        return ParseNextAction.change_document_type
    if parse_state == ParseState.parsed_awaiting_review:
        return ParseNextAction.review_fields
    if parse_state == ParseState.accepted_or_overridden:
        return ParseNextAction.review_or_promote
    return ParseNextAction.none


def build_parse_state_summary(file: FileModel, db_session: Session) -> ParseStateSummary:
    """Build the read-only :class:`ParseStateSummary` for a single file version."""
    document = file.document
    doc_enum = document.name if document else None
    doc_type_value = doc_enum.value if doc_enum else None

    # --- selected document type classification (read-only registry lookup) ---
    handler = AIParsingHandler(db_session)
    config = handler.get_extraction_config(doc_type_value) if doc_type_value else None
    schema_field_names = set()
    if config and config.get("fields"):
        schema_field_names = {f["name"] for f in config["fields"]}

    is_generic_stub = bool(schema_field_names) and schema_field_names == GENERIC_CONTRACTUAL_FIELD_SET
    is_equipment_type = doc_enum in EQUIPMENT_DOCUMENT_TYPES

    # --- parse runs (ordered by extraction_run_number DESC) ---
    crud = AIParsingResultCRUD(db_session)
    runs = crud.get_runs_for_file(file.id)
    latest_run = runs[0] if runs else None
    completed_runs = [r for r in runs if r.status == FileParsingStatuses.completed]
    latest_completed = completed_runs[0] if completed_runs else None

    # --- counts ---
    reviewable_field_count = 0
    parsed_values: dict = {}
    if latest_completed is not None:
        parsed_values = _extract_parsed_field_values(latest_completed)
        if schema_field_names:
            reviewable_field_count = sum(1 for key in parsed_values if key in schema_field_names)

    # Accepted/overridden keys are counted only for THIS file version (file_id ==
    # file.id), never legacy NULL-file keys, so a new version does not inherit an
    # older version's accepted state.
    accepted_overridden_count = (
        db_session.query(DocumentKey)
        .filter(
            DocumentKey.file_id == file.id,
            DocumentKey.status.in_(ACCEPTED_KEY_STATUSES),
        )
        .count()
    )

    promoted_count = (
        db_session.query(ProjectFact)
        .filter(
            ProjectFact.source_file_id == file.id,
            ProjectFact.status == FactStatus.active.value,
        )
        .count()
    )

    # --- state precedence (most-advanced durable state wins) ---
    no_usable_fields_reason: Optional[NoUsableFieldsReason] = None
    if promoted_count > 0:
        parse_state = ParseState.promoted
    elif accepted_overridden_count > 0:
        parse_state = ParseState.accepted_or_overridden
    elif latest_completed is not None:
        if reviewable_field_count > 0:
            parse_state = ParseState.parsed_awaiting_review
        else:
            parse_state = ParseState.parsed_no_usable_fields
            no_usable_fields_reason = _classify_no_usable_reason(
                schema_field_names, parsed_values, is_generic_stub
            )
    elif latest_run is not None and latest_run.status in FAILURE_STATUSES:
        parse_state = ParseState.parse_failed
    elif latest_run is not None and latest_run.status in IN_PROGRESS_STATUSES:
        parse_state = ParseState.parsing_in_progress
    else:
        parse_state = ParseState.not_yet_parsed

    # A newer queued/processing run over already-durable data must not regress the
    # summary back to "in progress" (that would hide reviewable/accepted data).
    active_reprocess_in_progress = bool(
        latest_run is not None
        and latest_run.status in IN_PROGRESS_STATUSES
        and parse_state not in (ParseState.parsing_in_progress, ParseState.not_yet_parsed)
    )

    # --- file version info ---
    non_deleted = [f for f in document.files if not f.deleted] if document else [file]
    is_sole_version = len(non_deleted) == 1 and non_deleted[0].id == file.id

    # --- warnings (stable codes; the UI maps these to copy) ---
    warnings: list[str] = []
    if not file.is_current_version:
        warnings.append("sole_non_current_version" if is_sole_version else "not_current_version")
    if is_equipment_type and is_generic_stub:
        warnings.append("no_equipment_extraction_schema")
    elif is_generic_stub:
        warnings.append("generic_contractual_schema")
    if parse_state == ParseState.parse_failed:
        warnings.append("parse_failed")

    next_action = _next_action(parse_state, is_equipment_type, is_generic_stub)

    last_parse_attempt_at = None
    latest_run_schema = None
    if latest_run is not None:
        last_parse_attempt_at = latest_run.start_time or latest_run.created_at
        latest_run_schema = ParseStateLatestRunSchema(
            id=latest_run.id,
            status=latest_run.status.value if latest_run.status else "unknown",
            extraction_run_number=latest_run.extraction_run_number,
            created_at=latest_run.created_at,
            start_time=latest_run.start_time,
            end_time=latest_run.end_time,
        )

    return ParseStateSummary(
        file_id=file.id,
        parse_state=parse_state,
        selected_document_type=SelectedDocumentTypeSchema(
            key=doc_enum.name if doc_enum else None,
            display=doc_type_value,
            is_generic_contractual_stub=is_generic_stub,
            is_equipment_type=is_equipment_type,
        ),
        file_version=ParseStateFileVersionSchema(
            id=file.id,
            is_current_version=file.is_current_version,
            is_sole_version=is_sole_version,
            version_display=file.version_display,
        ),
        last_parse_attempt_at=last_parse_attempt_at,
        latest_run=latest_run_schema,
        reviewable_field_count=reviewable_field_count,
        accepted_overridden_count=accepted_overridden_count,
        promoted_count=promoted_count,
        no_usable_fields_reason=no_usable_fields_reason,
        next_action=next_action,
        active_reprocess_in_progress=active_reprocess_in_progress,
        warnings=warnings,
    )


class ParseStateIndicators(NamedTuple):
    """Additive, read-only parse-lifecycle signals for one source file version.

    Consumed by the reconciliation aggregator purely as informational fields; it
    never feeds status/blocking/needs_review/baseline logic. Derived from
    :func:`build_parse_state_summary`, so the two surfaces stay consistent.
    """

    source_document_uploaded_not_parsed: bool
    parse_failed: bool
    parsed_no_usable_fields: bool
    source_document_not_current_version: bool
    source_document_type_lacks_operational_schema: bool


def compute_parse_state_indicators(file: FileModel, db_session: Session) -> ParseStateIndicators:
    """Map a file version's :class:`ParseStateSummary` to the additive indicator
    booleans. Strictly read-only (delegates to ``build_parse_state_summary``)."""
    summary = build_parse_state_summary(file, db_session)
    return ParseStateIndicators(
        source_document_uploaded_not_parsed=summary.parse_state == ParseState.not_yet_parsed,
        parse_failed=summary.parse_state == ParseState.parse_failed,
        parsed_no_usable_fields=summary.parse_state == ParseState.parsed_no_usable_fields,
        source_document_not_current_version=not summary.file_version.is_current_version,
        source_document_type_lacks_operational_schema=(
            summary.selected_document_type.is_generic_contractual_stub
        ),
    )
