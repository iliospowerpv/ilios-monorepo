#!/usr/bin/env python3
"""
Seed Extraction Registry from ai_parsing_config.json

This script populates the extraction registry with:
1. Document types from the parsing config
2. Schema version v1 for each doc type with corresponding fields
3. Prompt template v1 for each doc type with default templates

Usage:
    python dev_scripts/seed_extraction_registry.py

The script is idempotent - running it multiple times won't create duplicates.
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionFactory
from app.db.base import (
    CanonicalField,
    ExtractionDocumentType,
    ExtractionSchemaVersion,
    ExtractionSchemaVersionField,
    ExtractionPromptTemplate,
)
from app.models.extraction_registry import DEFAULT_SYSTEM_PROMPT, DEFAULT_EXTRACTION_PROMPT


def normalize_doc_type_name(display_name: str) -> str:
    normalized = display_name.lower()
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    normalized = re.sub(r'\s+', '_', normalized.strip())
    return normalized


def normalize_field_name(display_name: str) -> str:
    normalized = display_name.lower()
    normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
    normalized = re.sub(r'\s+', '_', normalized.strip())
    return normalized


def infer_field_type(key_name: str) -> str:
    key_lower = key_name.lower()
    if 'date' in key_lower:
        return 'date'
    if 'amount' in key_lower or 'rate' in key_lower or 'size' in key_lower:
        return 'currency'
    if '(y/n)' in key_lower:
        return 'boolean'
    if 'percentage' in key_lower or 'escalator' in key_lower:
        return 'percentage'
    return 'text'


def categorize_doc_type(name: str) -> str:
    name_lower = name.lower()
    if any(x in name_lower for x in ['agreement', 'contract', 'lease', 'ppa', 'oma']):
        return 'legal'
    if any(x in name_lower for x in ['pvsyst', 'technical', 'interconnection', 'appraisal']):
        return 'technical'
    if any(x in name_lower for x in ['tax', 'loan', 'title', 'insurance', 'finance']):
        return 'financial'
    return 'other'


def seed_extraction_registry():
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'configs',
        'ai_parsing_config.json'
    )

    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = json.load(f)

    db = SessionFactory()
    try:
        stats = {
            'doc_types_created': 0,
            'doc_types_skipped': 0,
            'schema_versions_created': 0,
            'prompt_templates_created': 0,
            'fields_linked': 0,
        }

        for doc_type_display_name, field_keys in config.items():
            doc_type_name = normalize_doc_type_name(doc_type_display_name)
            print(f"\n=== Processing: {doc_type_display_name} ({doc_type_name}) ===")

            existing_doc_type = db.query(ExtractionDocumentType).filter(
                ExtractionDocumentType.name == doc_type_name
            ).first()

            if existing_doc_type:
                print(f"  SKIP: Document type already exists (id={existing_doc_type.id})")
                stats['doc_types_skipped'] += 1
                doc_type = existing_doc_type
            else:
                doc_type = ExtractionDocumentType(
                    name=doc_type_name,
                    display_name=doc_type_display_name,
                    category=categorize_doc_type(doc_type_name),
                    is_parsable=True,
                    is_active=True,
                )
                db.add(doc_type)
                db.flush()
                print(f"  CREATE: Document type (id={doc_type.id})")
                stats['doc_types_created'] += 1

            existing_schema = db.query(ExtractionSchemaVersion).filter(
                ExtractionSchemaVersion.document_type_id == doc_type.id
            ).first()

            if existing_schema:
                print(f"  SKIP: Schema version already exists (v{existing_schema.version})")
                schema_version = existing_schema
            else:
                schema_version = ExtractionSchemaVersion(
                    document_type_id=doc_type.id,
                    version=1,
                    is_active=True,
                    notes="Initial version from ai_parsing_config.json seed",
                )
                db.add(schema_version)
                db.flush()
                print(f"  CREATE: Schema version v1 (id={schema_version.id})")
                stats['schema_versions_created'] += 1

            existing_fields = db.query(ExtractionSchemaVersionField).filter(
                ExtractionSchemaVersionField.schema_version_id == schema_version.id
            ).count()

            if existing_fields > 0:
                print(f"  SKIP: Schema already has {existing_fields} fields linked")
            else:
                for priority, field_display_name in enumerate(field_keys, start=1):
                    field_name = normalize_field_name(field_display_name)

                    canonical_field = db.query(CanonicalField).filter(
                        CanonicalField.name == field_name
                    ).first()

                    if not canonical_field:
                        canonical_field = CanonicalField(
                            name=field_name,
                            display_name=field_display_name,
                            field_type=infer_field_type(field_display_name),
                            is_active=True,
                        )
                        db.add(canonical_field)
                        db.flush()
                        print(f"    CREATE field: {field_name}")

                    existing_link = db.query(ExtractionSchemaVersionField).filter(
                        ExtractionSchemaVersionField.schema_version_id == schema_version.id,
                        ExtractionSchemaVersionField.canonical_field_id == canonical_field.id
                    ).first()

                    if not existing_link:
                        link = ExtractionSchemaVersionField(
                            schema_version_id=schema_version.id,
                            canonical_field_id=canonical_field.id,
                            is_required=False,
                            extraction_priority=priority * 10,
                        )
                        db.add(link)
                        stats['fields_linked'] += 1

                print(f"  LINK: {len(field_keys)} fields to schema v1")

            existing_prompt = db.query(ExtractionPromptTemplate).filter(
                ExtractionPromptTemplate.document_type_id == doc_type.id
            ).first()

            if existing_prompt:
                print(f"  SKIP: Prompt template already exists (v{existing_prompt.version})")
            else:
                prompt = ExtractionPromptTemplate(
                    document_type_id=doc_type.id,
                    version=1,
                    is_active=True,
                    system_prompt=DEFAULT_SYSTEM_PROMPT,
                    extraction_prompt=DEFAULT_EXTRACTION_PROMPT,
                    model_name="claude-sonnet-4-5",
                    temperature=0.0,
                    max_tokens=8000,
                    notes="Initial version from seed",
                )
                db.add(prompt)
                print(f"  CREATE: Prompt template v1")
                stats['prompt_templates_created'] += 1

        db.commit()

        print("\n" + "=" * 50)
        print("SEED COMPLETE")
        print("=" * 50)
        print(f"Document types created: {stats['doc_types_created']}")
        print(f"Document types skipped: {stats['doc_types_skipped']}")
        print(f"Schema versions created: {stats['schema_versions_created']}")
        print(f"Prompt templates created: {stats['prompt_templates_created']}")
        print(f"Fields linked to schemas: {stats['fields_linked']}")

    except Exception as e:
        db.rollback()
        print(f"\nERROR: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_extraction_registry()
