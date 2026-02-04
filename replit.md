# iliOS - REA Investment Platform

## Overview
iliOS is a real estate asset investment management platform designed to manage the entire lifecycle of real estate investments, from acquisition and due diligence to asset management, financial tracking, and reporting. The platform aims to enhance decision-making through data-driven insights and improve operational efficiency for real estate investors and asset managers. Key capabilities include secure user authentication, multi-company user membership, a user-centric workspace, comprehensive asset and task management, financial oversight with budgeting and vendor management, sales pipeline tracking, and robust reporting tools. iliOS serves as a centralized system for investment oversight and operational governance for real estate professionals.

## User Preferences
I prefer detailed explanations and thorough documentation for any implemented features or architectural decisions.
I expect iterative development, with clear communication before significant changes are made.
Do not change the fundamental "Site" entity in the backend; use "Project" only as a UI terminology update.

## System Architecture

### Frontend
- **Technology Stack**: React 18, TypeScript, Material UI (MUI), React Query, React Router DOM, AG Grid, Chart.js, Webpack 5.
- **UI/UX Decisions**: Standardized "Projects" terminology, robust navigation (Entity Context, Module Sidebar, Breadcrumb), a unified Context Bar for scope management, a static Asset Management Overview with drag-and-drop features, a collapsible sidebar, and consolidated admin/settings modules for improved user experience and access control.

### Backend
- **Technology Stack**: Python 3.11, FastAPI, SQLAlchemy, Alembic, PostgreSQL.
- **Core Modules**: Workspace, Finance (capital governance, budgeting, vendor management), Acquisitions (13-stage deal pipeline), and Project Hub (unified asset management and due diligence).
- **Access Control**: Multi-Company Access System, Canonical Effective-Access Resolver for granular authorization (fail-closed, restrict-only semantics), and Module-Level Permission Enforcement with `permission_guards.py`.
- **Diligence Module**: Migrated to canonical permission guards for all endpoints.
- **Role Profiles System**: Granular stakeholder role definitions augmenting base roles.
- **Portfolio Hub Boundary Model**: Links companies within a hub for controlled data visibility.
- **Architectural Guardrails**: Asset Management Overview is a static record, linking to operational modules for live metrics.
- **Telemetry Module**: Project-scoped telemetry for Data Acquisition Systems (DAS) integration, health monitoring, and device mapping CRUD with Firestore sync.
- **Document Versioning & Promotion System**: Implements lender-quality Data Room document versioning with "Promote to Current Assumptions" workflow, managing `candidate`, `active`, and `retired` `ProjectFact` states with atomic transactions and diff computation.
- **Extraction Registry & Prompt Studio**: Scalable system for dynamic document type and field configuration using database-driven schemas, prompt templates, and an `ExtractionPipelineService` with registry-first lookup. Supports re-extraction workflows with binding snapshots for auditability. Includes an Admin API and UI for management.
- **In-App AI Parsing (Replit-Native)**: Fully in-app document parsing using Replit AI Integrations (OpenAI), removing external cloud function dependencies. Features `InAppParsingService` for file handling, text extraction (PDF, DOCX), LLM calls via FastAPI BackgroundTasks, observability with correlation IDs, and retry logic with exponential backoff.
    - **Phase 2A Idempotency & Concurrency Safety**: Prevents duplicate parsing and race conditions:
        - New `queued` status. Jobs created as `queued`, then atomically claimed to `processing`.
        - Partial unique index `ix_ai_parsing_results_active_unique` on (file_id, COALESCE(document_type_id, -1), COALESCE(schema_version_id, -1), COALESCE(prompt_template_id, -1)) WHERE status IN ('queued', 'processing') enforces idempotency at DB level.
        - `create_or_get_active()` uses IntegrityError handling for concurrent request safety.
        - `atomic_claim()` uses `SELECT ... FOR UPDATE` row locking for background task safety.
        - Claim columns: `worker_id`, `correlation_id`, `claimed_at`.
        - Terminal state guarantees: `mark_completed()` and `mark_failed()` always set `end_time`.
    - **Phase 2B E2E Integration Tests**: Comprehensive test coverage for parsing pipeline:
        - LLM Stub: `app/services/llm_stub.py` provides deterministic stub via `enable_llm_stub()` / `disable_llm_stub()`.
        - Injection: Set `LLM_STUB_ENABLED=true` env var; `InAppParsingService.call_llm()` auto-detects and uses stub.
        - Happy path: Trigger → claim → process → completed with parsed_result and binding snapshots.
        - Idempotency: Double-trigger returns existing run; force reprocess bypasses.
        - Failure path: LLM/storage exceptions → `processing_failed` with error_message and end_time.
    - **Phase 2B.1 Trigger Response Identifiers & Safe Stub Gating**:
        - **Trigger Response Fields**: `FileParseTriggerSuccess` now includes:
            - `run_id` (int): AIParsingResult.id for the created/existing job
            - `correlation_id` (str): UUID for request tracing
            - `status` (str): Current job status ("queued", "processing", etc.)
            - `code` (int): HTTP status code (202)
            - `message` (str): Success message
        - **Idempotency Behavior**: Duplicate triggers return the EXISTING run_id, correlation_id, and current status.
        - **LLM Stub Safety Gating**:
            - Stub can ONLY be enabled in safe environments: test, testing, dev, development, local, debug.
            - Blocked environments: production, prod, staging (stub always disabled).
            - `enable_llm_stub()` raises `RuntimeError` if called in production.
            - `is_llm_stub_enabled()` returns False in production regardless of env var.
            - Pytest detection: `PYTEST_CURRENT_TEST` env var auto-allows stub.
    - **Phase 3A Field Key Mapping & UI Integration**: Ensures AI-extracted fields display correctly in the UI:
        - Prompt template sends exact canonical field keys (e.g., `- lessor_landlord_entity_name: Lessor (Landlord) Entity Name`)
        - LLM instructed to use exact field_key before the colon
        - `combine_user_ai_parsing_results()` builds display_name ↔ canonical_name mapping
        - AI results matched using canonical names, displayed using display names
        - Fixed `.format()` → `.replace()` to handle JSON braces in prompt templates
    - **Phase 3 Quality Guardrails & Resource Limits**: Prevents low-quality or oversized inputs from causing cost/latency spikes:
        - **Configurable Settings** (in `app/settings.py`):
            - `parsing_min_text_chars`: Minimum extracted chars (default: 500). Below threshold suggests scanned/image PDF.
            - `parsing_max_file_size_mb`: Maximum file size in MB (default: 25).
            - `parsing_max_pdf_pages`: Maximum PDF pages (default: 200).
            - `parsing_max_chars_to_llm`: Maximum chars sent to LLM (default: 200,000). Text truncated beyond this.
        - **Reason Codes** (`ParsingReasonCode` enum): Machine-readable failure identifiers stored in `error_message` with `[reason_code]` prefix:
            - `file_too_large`: File exceeds max size limit.
            - `too_many_pages`: PDF exceeds max page limit.
            - `insufficient_text_extracted`: Extracted text below minimum threshold (suggests OCR needed).
            - `unsupported_file_type`: File extension not supported.
            - `text_extraction_failed`: PDF/DOCX parsing error.
            - `llm_call_failed`: OpenAI API call failed.
            - `no_extraction_config`: No extraction config found for document type.
            - `storage_error`: File download from storage failed.
        - **Extraction Metadata**: Successful parses include `char_count`, `word_count`, `page_count`, `was_truncated`, `truncated_char_count` in response metadata.
        - **Truncation Behavior**: Text exceeding `parsing_max_chars_to_llm` is truncated at nearest newline boundary with warning logged.
- **Storage Service Abstraction**: Replit-native storage architecture with an abstract `StorageService` interface, `ReplitStorageService` (default), optional `GCSStorageService`, and `HybridStorageService` for migration support. Utilizes new direct upload and download endpoints.
- **Data Room Parsing UX (Phase B1)**: User-friendly parsing status display in the Document Modal:
    - **Status Badge**: Visual indicator showing Queued, Processing (with spinner), Completed, or Failed states.
    - **Reason Code Mapping**: Backend error codes (`[reason_code]` prefix) mapped to user-friendly messages:
        - `insufficient_text_extracted` → "This document appears to be scanned. OCR is required."
        - `file_too_large` → "This file exceeds the maximum supported size."
        - `too_many_pages` → "This PDF exceeds the maximum supported page count."
        - `unsupported_file_type` → "This file type is not supported."
        - `llm_call_failed` → "AI parsing failed. Please try again."
        - `storage_error` → "Unable to read file from storage."
    - **Truncation Warning**: Alert banner shown when `was_truncated=true` with character counts.
    - **Metadata Display**: Page count, character count, word count chips for completed parses.
    - **Debug Section**: Expandable accordion showing `run_id` and `correlation_id` for troubleshooting.
    - **Reprocess Action**: Button to force re-parse with `force_reprocess=true`; disabled during processing.
    - **Polling**: Auto-refresh status every 5 seconds while processing is active.
- **Data Room PDF Viewer & Evidence Navigation (Phase B2)**:
    - **Hybrid Viewer Architecture**: Uses `@react-pdf-viewer` for PDFs (with jump-to-page and search highlight), `react-doc-viewer` for DOCX and other formats.
    - **PDFViewer Component** (`frontend/.../components/PDFViewer.tsx`): Custom wrapper around `@react-pdf-viewer/core` with plugins:
        - `pageNavigationPlugin`: Enables `jumpToPage(pageNumber)` for programmatic page navigation.
        - `searchPlugin`: Enables `highlight({ keyword })` for text search and highlight.
        - Exposes `PDFViewerRef` with `jumpToPage(page)` and `searchAndHighlight(text)` methods.
    - **Evidence Navigation Flow**:
        1. Backend returns `evidence: { page, snippet, anchor_text }` per extracted field.
        2. Frontend displays "Page X" button with tooltip showing snippet.
        3. On click: calls `pdfViewerRef.jumpToPage(page)`, then `searchAndHighlight(anchor_text || snippet)`.
        4. Non-PDF files show "Jump-to-page is available for PDFs only" message.
    - **Worker Configuration**: Uses PDF.js worker from CDN: `https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js`.
- **Data Room Evidence & Acceptance Workflow (Phase B3)**:
    - **Evidence Coverage Audit**: Verified 100% evidence coverage - all AI-extracted fields include `page`, `snippet`, and `anchor_text` for source provenance.
    - **No Evidence Indicator**: Fields lacking evidence display a "No evidence" chip for visual clarity.
    - **Verify All Navigation**: Sequential field verification workflow with "Prev" / "Next" buttons and "X / Y" counter. Filters to fields with evidence, jumps to corresponding PDF page and highlights anchor text.
    - **Accept All Bulk Action**: Confirmation dialog showing count of fields to accept, with warning count for fields without evidence. Uses `bulkAcceptAIValues` API method for batch updates to `setDocumentKeyValue`.
    - **Reprocess CTA**: Existing reprocess button allows re-triggering AI parsing from failed state with `force_reprocess=true`.

## External Dependencies
- **PostgreSQL**: Primary relational database.
- **Redis**: Used for caching and session management.
- **PowerBI**: Integrated for reporting and business intelligence.
- **Mailgun**: Configured for email services.
- **Rombus**: Integrated for camera/security functionalities.
- **AG Grid**: Enterprise license for advanced table functionalities.