"""Project Import Router - Bulk import projects from CSV/XLSX files."""

import csv
import io
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.crud.company import CompanyCRUD
from app.crud.site import SiteCRUD
from app.crud.user_project import UserProjectCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.due_diligence.due_diligence_helper import (
    create_default_site_document_sections,
    generate_default_site_documents,
)
from app.helpers.permission_guards import require_module_permission
from app.helpers.task_tracker.board_defaults_helper import create_default_board, create_default_document_tasks
from app.models.board import BoardModuleEnum, BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum
from app.models.site import State
from app.crud.document import DocumentCRUD
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE
from app.static.permissions import PermissionsModules

logger = logging.getLogger(__name__)
project_import_router = APIRouter()


def _validate_company_exists(db_session: Session, company_id: int):
    company = CompanyCRUD(db_session).get_item(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found."
        )

VALID_STATES = {s.value.upper(): s.value for s in State}

KNOWN_TARGET_FIELDS = [
    "project_name",
    "address",
    "city",
    "state",
    "zip_code",
    "county",
    "system_size_ac",
    "system_size_dc",
    "latitude",
    "longitude",
    "coordinates",
    "lon_lat_url",
    "status",
    "notes",
]

FIELD_DISPLAY_NAMES = {
    "project_name": "Project Name",
    "address": "Address",
    "city": "City",
    "state": "State",
    "zip_code": "ZIP Code",
    "county": "County",
    "system_size_ac": "System Size AC (kW)",
    "system_size_dc": "System Size DC (kW)",
    "latitude": "Latitude",
    "longitude": "Longitude",
    "coordinates": "Coordinates",
    "lon_lat_url": "Coordinates URL",
    "status": "Status",
    "notes": "Notes",
}

AUTO_MAP_HINTS: Dict[str, List[str]] = {
    "project_name": ["project name", "name", "project", "site name", "site"],
    "address": ["address", "street", "street address", "project address", "site address"],
    "city": ["city", "town"],
    "state": ["state", "st"],
    "zip_code": ["zip", "zip code", "zipcode", "zip_code", "postal code", "postal"],
    "county": ["county"],
    "system_size_ac": ["system size ac", "ac size", "ac capacity", "ac kw", "size ac", "capacity ac", "ac_kw", "system_size_ac", "mw ac"],
    "system_size_dc": ["system size dc", "dc size", "dc capacity", "dc kw", "size dc", "capacity dc", "dc_kw", "system_size_dc", "mw dc"],
    "latitude": ["latitude", "lat"],
    "longitude": ["longitude", "lng", "lon", "long"],
    "coordinates": ["coordinates", "coords", "gps", "lat/long", "lat/lon", "location"],
    "lon_lat_url": ["lon_lat_url", "coordinates url", "google maps", "map url", "map link"],
    "status": ["status", "project status", "site status"],
    "notes": ["notes", "comments", "description", "memo"],
}


class ColumnMapping(BaseModel):
    source_column: str
    target_field: str


class ImportRequest(BaseModel):
    column_mappings: List[ColumnMapping]
    skip_duplicates: bool = True
    file_content: Optional[str] = None


class RowError(BaseModel):
    row: int
    field: str
    message: str


class ImportRowResult(BaseModel):
    row: int
    status: str
    project_id: Optional[int] = None
    project_name: Optional[str] = None
    errors: List[RowError] = []


class ImportResultSchema(BaseModel):
    batch_id: str
    total_rows: int
    imported: int
    skipped: int
    failed: int
    results: List[ImportRowResult]
    source_file: Optional[str] = None


class ParsedFileResponse(BaseModel):
    headers: List[str]
    sample_rows: List[Dict[str, Any]]
    total_rows: int
    suggested_mappings: Dict[str, str] = {}


class ValidateResponse(BaseModel):
    total_rows: int
    valid_rows: int
    invalid_rows: int
    duplicate_rows: int
    row_results: List[ImportRowResult]


def parse_csv_content(content: bytes) -> tuple[list[str], list[dict]]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    headers = reader.fieldnames or []
    rows = [dict(row) for row in reader]
    return headers, rows


def parse_xlsx_content(content: bytes) -> tuple[list[str], list[dict]]:
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    header_row = next(rows_iter, None)
    if not header_row:
        return [], []
    headers = [str(h).strip() if h is not None else f"Column_{i}" for i, h in enumerate(header_row)]
    rows = []
    for row_values in rows_iter:
        if all(v is None for v in row_values):
            continue
        row_dict = {}
        for i, val in enumerate(row_values):
            if i < len(headers):
                row_dict[headers[i]] = str(val).strip() if val is not None else ""
        rows.append(row_dict)
    wb.close()
    return headers, rows


def parse_file(content: bytes, filename: str) -> tuple[list[str], list[dict]]:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "csv":
        try:
            return parse_csv_content(content)
        except (UnicodeDecodeError, csv.Error) as e:
            logger.warning(f"CSV parse error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to parse CSV file. Please ensure it is a valid UTF-8 encoded CSV."
            )
    elif ext == "xlsx":
        try:
            return parse_xlsx_content(content)
        except Exception as e:
            logger.warning(f"XLSX parse error: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to parse XLSX file. Please ensure it is a valid Excel (.xlsx) file."
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: .{ext}. Use .csv or .xlsx"
        )


def suggest_mappings(headers: list[str]) -> dict[str, str]:
    mappings = {}
    used_targets = set()
    for header in headers:
        normalized = header.strip().lower().replace("_", " ")
        for target_field, hints in AUTO_MAP_HINTS.items():
            if target_field in used_targets:
                continue
            if normalized in hints:
                mappings[header] = target_field
                used_targets.add(target_field)
                break
    return mappings


def parse_coordinates(coord_str: str) -> tuple[Optional[float], Optional[float]]:
    if not coord_str or not coord_str.strip():
        return None, None
    coord_str = coord_str.strip()
    for sep in [",", " "]:
        parts = [p.strip() for p in coord_str.split(sep) if p.strip()]
        if len(parts) == 2:
            try:
                lat = float(parts[0])
                lon = float(parts[1])
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return lat, lon
            except ValueError:
                continue
    return None, None


def validate_row(
    row_data: dict,
    row_num: int,
    mappings: dict[str, str],
    existing_names: set[str],
) -> tuple[dict, list[RowError]]:
    errors: list[RowError] = []
    mapped: dict[str, Any] = {}

    for source_col, target_field in mappings.items():
        raw_value = row_data.get(source_col, "").strip()
        mapped[target_field] = raw_value

    name = mapped.get("project_name", "").strip()
    if not name:
        errors.append(RowError(row=row_num, field="project_name", message="Project Name is required"))
    elif name.lower() in existing_names:
        errors.append(RowError(row=row_num, field="project_name", message=f"Duplicate project name: '{name}'"))

    address = mapped.get("address", "").strip()
    if not address:
        errors.append(RowError(row=row_num, field="address", message="Address is required"))

    city = mapped.get("city", "").strip()
    if not city:
        errors.append(RowError(row=row_num, field="city", message="City is required"))

    state_raw = mapped.get("state", "").strip().upper()
    if not state_raw:
        errors.append(RowError(row=row_num, field="state", message="State is required"))
    elif state_raw not in VALID_STATES:
        errors.append(RowError(row=row_num, field="state", message=f"Invalid state: '{state_raw}'. Use 2-letter code (e.g. CA, NY)"))

    zip_code = mapped.get("zip_code", "").strip()
    if not zip_code:
        errors.append(RowError(row=row_num, field="zip_code", message="ZIP Code is required"))
    else:
        zip_digits = zip_code.replace("-", "").replace(" ", "")
        if not zip_digits[:5].isdigit():
            errors.append(RowError(row=row_num, field="zip_code", message=f"Invalid ZIP code: '{zip_code}'"))
        else:
            mapped["zip_code"] = zip_digits[:5]

    for size_field in ["system_size_ac", "system_size_dc"]:
        val = mapped.get(size_field, "").strip()
        if val:
            try:
                mapped[size_field] = round(float(val), 2)
            except ValueError:
                errors.append(RowError(row=row_num, field=size_field, message=f"Invalid number: '{val}'"))
                mapped[size_field] = None
        else:
            mapped[size_field] = 0.0

    lat_val = None
    lon_val = None
    if mapped.get("coordinates"):
        lat_val, lon_val = parse_coordinates(mapped["coordinates"])
        if lat_val is None and mapped["coordinates"].strip():
            errors.append(RowError(row=row_num, field="coordinates", message=f"Invalid coordinates format: '{mapped['coordinates']}'"))
    if mapped.get("latitude"):
        try:
            lat_val = float(mapped["latitude"])
            if not (-90 <= lat_val <= 90):
                errors.append(RowError(row=row_num, field="latitude", message=f"Latitude must be between -90 and 90, got {lat_val}"))
                lat_val = None
        except ValueError:
            errors.append(RowError(row=row_num, field="latitude", message=f"Invalid latitude: '{mapped['latitude']}'"))
    if mapped.get("longitude"):
        try:
            lon_val = float(mapped["longitude"])
            if not (-180 <= lon_val <= 180):
                errors.append(RowError(row=row_num, field="longitude", message=f"Longitude must be between -180 and 180, got {lon_val}"))
                lon_val = None
        except ValueError:
            errors.append(RowError(row=row_num, field="longitude", message=f"Invalid longitude: '{mapped['longitude']}'"))

    if lat_val is not None and lon_val is not None:
        mapped["_lon_lat_url"] = f"{lat_val}, {lon_val}"
    elif mapped.get("lon_lat_url"):
        mapped["_lon_lat_url"] = mapped["lon_lat_url"]
    else:
        mapped["_lon_lat_url"] = ""

    if not mapped["_lon_lat_url"]:
        mapped["_lon_lat_url"] = "N/A"

    return mapped, errors


@project_import_router.post(
    "/parse",
    response_model=ParsedFileResponse,
    responses={**HTTP_403_RESPONSE},
)
async def parse_import_file(
    company_id: int = Query(...),
    file: UploadFile = File(...),
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
) -> dict:
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.assets_management.value,
        action="edit",
    )
    _validate_company_exists(db_session, company_id)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    headers, rows = parse_file(content, file.filename or "unknown.csv")
    if not headers:
        raise HTTPException(status_code=400, detail="No headers found in file")

    sample_rows = rows[:5]
    suggested = suggest_mappings(headers)

    return {
        "headers": headers,
        "sample_rows": sample_rows,
        "total_rows": len(rows),
        "suggested_mappings": suggested,
    }


@project_import_router.post(
    "/validate",
    response_model=ValidateResponse,
    responses={**HTTP_403_RESPONSE},
)
async def validate_import(
    company_id: int = Query(...),
    file: UploadFile = File(...),
    mappings_json: str = Query(..., description="JSON string of column mappings"),
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
) -> dict:
    import json

    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.assets_management.value,
        action="edit",
    )
    _validate_company_exists(db_session, company_id)

    try:
        mappings_list = json.loads(mappings_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid mappings JSON")

    column_mappings = {m["source_column"]: m["target_field"] for m in mappings_list}
    content = await file.read()
    headers, rows = parse_file(content, file.filename or "unknown.csv")

    site_crud = SiteCRUD(db_session)
    _, existing_sites = site_crud.get_sites_by_company_id(company_id, skip_pagination=True)
    existing_names = {s.name.lower() for s in existing_sites}

    row_results = []
    valid_count = 0
    invalid_count = 0
    duplicate_count = 0
    seen_names: set[str] = set()

    for i, row in enumerate(rows):
        row_num = i + 2
        mapped, errors = validate_row(row, row_num, column_mappings, existing_names)
        name = mapped.get("project_name", "").strip().lower()

        is_duplicate = False
        if name and name in existing_names:
            is_duplicate = True
            duplicate_count += 1
        elif name and name in seen_names:
            is_duplicate = True
            duplicate_count += 1
            errors.append(RowError(row=row_num, field="project_name", message=f"Duplicate within file: '{mapped.get('project_name', '')}'"))

        if name:
            seen_names.add(name)

        if errors:
            invalid_count += 1
            row_results.append(ImportRowResult(
                row=row_num,
                status="invalid",
                project_name=mapped.get("project_name", ""),
                errors=errors,
            ))
        elif is_duplicate:
            row_results.append(ImportRowResult(
                row=row_num,
                status="duplicate",
                project_name=mapped.get("project_name", ""),
                errors=[RowError(row=row_num, field="project_name", message="Duplicate project name")],
            ))
        else:
            valid_count += 1
            row_results.append(ImportRowResult(
                row=row_num,
                status="valid",
                project_name=mapped.get("project_name", ""),
            ))

    return {
        "total_rows": len(rows),
        "valid_rows": valid_count,
        "invalid_rows": invalid_count,
        "duplicate_rows": duplicate_count,
        "row_results": row_results,
    }


@project_import_router.post(
    "/execute",
    response_model=ImportResultSchema,
    responses={**HTTP_403_RESPONSE},
)
async def execute_import(
    company_id: int = Query(...),
    file: UploadFile = File(...),
    mappings_json: str = Query(..., description="JSON string of column mappings"),
    skip_duplicates: bool = Query(True),
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
) -> dict:
    import json

    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.assets_management.value,
        action="edit",
    )
    _validate_company_exists(db_session, company_id)

    try:
        mappings_list = json.loads(mappings_json)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid mappings JSON")

    column_mappings = {m["source_column"]: m["target_field"] for m in mappings_list}
    content = await file.read()
    headers, rows = parse_file(content, file.filename or "unknown.csv")

    site_crud = SiteCRUD(db_session)
    _, existing_sites = site_crud.get_sites_by_company_id(company_id, skip_pagination=True)
    existing_names = {s.name.lower() for s in existing_sites}

    batch_id = str(uuid.uuid4())[:8]
    results: List[ImportRowResult] = []
    imported = 0
    skipped = 0
    failed = 0
    seen_names: set[str] = set()

    for i, row in enumerate(rows):
        row_num = i + 2
        mapped, errors = validate_row(row, row_num, column_mappings, existing_names)

        name = mapped.get("project_name", "").strip()
        name_lower = name.lower()

        if name_lower in existing_names or name_lower in seen_names:
            if skip_duplicates:
                skipped += 1
                results.append(ImportRowResult(
                    row=row_num,
                    status="skipped",
                    project_name=name,
                    errors=[RowError(row=row_num, field="project_name", message="Skipped duplicate")],
                ))
                continue
            else:
                errors.append(RowError(row=row_num, field="project_name", message="Duplicate project name"))

        if errors:
            failed += 1
            results.append(ImportRowResult(
                row=row_num,
                status="failed",
                project_name=name,
                errors=errors,
            ))
            continue

        state_val = VALID_STATES.get(mapped.get("state", "").strip().upper(), "")

        site_data = {
            "name": name,
            "address": mapped.get("address", "").strip(),
            "city": mapped.get("city", "").strip(),
            "state": state_val,
            "zip_code": mapped.get("zip_code", "").strip(),
            "county": mapped.get("county", "").strip() or None,
            "system_size_ac": mapped.get("system_size_ac", 0.0) if isinstance(mapped.get("system_size_ac"), (int, float)) else 0.0,
            "system_size_dc": mapped.get("system_size_dc", 0.0) if isinstance(mapped.get("system_size_dc"), (int, float)) else 0.0,
            "lon_lat_url": mapped.get("_lon_lat_url", "N/A"),
            "company_id": company_id,
            "cameras_uuids": [],
        }

        try:
            new_site = site_crud.create_item(site_data)
        except Exception as e:
            db_session.rollback()
            logger.exception(f"Import batch {batch_id}: Failed to create site '{name}': {e}")
            failed += 1
            results.append(ImportRowResult(
                row=row_num,
                status="failed",
                project_name=name,
                errors=[RowError(row=row_num, field="general", message="Failed to create project. Please check your data and try again.")],
            ))
            continue

        try:
            create_default_site_document_sections([new_site.id], db_session)
            DocumentCRUD(db_session).create_items(
                generate_default_site_documents([new_site.id], db_session)
            )
            create_default_board(new_site.id, BoardRelatedEntityTypeEnum.site, db_session)
            create_default_board(new_site.id, BoardRelatedEntityTypeEnum.site, db_session, module=BoardModuleEnum.om)
            create_default_board(
                new_site.id, BoardRelatedEntityTypeEnum.site, db_session, BoardRelatedEntityTypeExtraEnum.document
            )
            db_session.refresh(new_site)
            create_default_document_tasks(
                db_session, new_site.documents_board, new_site.documents, current_user.id, freeze_external_id=True
            )

            if not current_user.has_platform_bypass:
                UserProjectCRUD(db_session).create_item(
                    {"user_id": current_user.id, "site_id": new_site.id, "company_id": company_id}
                )
        except Exception as e:
            logger.warning(
                f"Import batch {batch_id}: Site '{name}' (id={new_site.id}) created but "
                f"initialization incomplete: {e}"
            )

        imported += 1
        existing_names.add(name_lower)
        seen_names.add(name_lower)
        results.append(ImportRowResult(
            row=row_num,
            status="imported",
            project_id=new_site.id,
            project_name=name,
        ))
        logger.info(f"Import batch {batch_id}: Created site '{name}' (id={new_site.id}) for company {company_id}")

    logger.info(
        f"Import batch {batch_id}: company={company_id}, user={current_user.id}, "
        f"total={len(rows)}, imported={imported}, skipped={skipped}, failed={failed}"
    )

    return {
        "batch_id": batch_id,
        "total_rows": len(rows),
        "imported": imported,
        "skipped": skipped,
        "failed": failed,
        "results": results,
        "source_file": file.filename,
    }
