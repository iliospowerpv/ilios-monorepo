#!/usr/bin/env python3
"""
Seed canonical_fields table from ai_parsing_config.json

This is a one-time bootstrap script to populate the canonical_fields table
from the existing extraction key definitions. After this, the database becomes
the source of truth for field definitions.

Usage:
    python dev_scripts/seed_canonical_fields.py
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionFactory
from app.db.base import CanonicalField  # noqa: F401 - Imports all models via base.py


def normalize_key_name(display_name: str) -> str:
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


def seed_canonical_fields():
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'configs',
        'ai_parsing_config.json'
    )
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    all_keys = set()
    for doc_type, keys in config.items():
        for key in keys:
            all_keys.add(key)
    
    db = SessionFactory()
    try:
        created_count = 0
        skipped_count = 0
        processed_names = set()
        
        for display_name in sorted(all_keys):
            name = normalize_key_name(display_name)
            
            if name in processed_names:
                print(f"SKIP: {name} (duplicate in input)")
                skipped_count += 1
                continue
            processed_names.add(name)
            
            field_type = infer_field_type(display_name)
            
            existing = db.query(CanonicalField).filter(
                CanonicalField.name == name
            ).first()
            
            if existing:
                print(f"SKIP: {name} already exists in DB")
                skipped_count += 1
                continue
            
            field = CanonicalField(
                name=name,
                display_name=display_name,
                field_type=field_type,
                is_active=True,
            )
            db.add(field)
            db.flush()  # Flush each record to catch conflicts immediately
            print(f"CREATE: {name} ({field_type})")
            created_count += 1
        
        db.commit()
        print(f"\n=== Summary ===")
        print(f"Created: {created_count}")
        print(f"Skipped: {skipped_count}")
        print(f"Total unique keys: {len(all_keys)}")
        
    finally:
        db.close()


if __name__ == "__main__":
    seed_canonical_fields()
