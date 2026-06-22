"""WS.3 — upstream device fingerprint (pure, additive, read-only).

A *fingerprint* is a small, deterministic snapshot of the UPSTREAM IDENTITY a
weather-semantics declaration was authored against: the governed mapping's stream
identity, the live device->provider telemetry link, and the device's stable
descriptors. It exists for ONE purpose — to let WS.3 detect when that upstream
identity has CHANGED since the declaration was made, so a human can be asked to
re-confirm the declared meaning (``needs_re_review``, a Layer-1 governance signal).

This module is pure: it reads only already-loaded ORM attributes and performs NO
database access, NO writes, and NO inference of weather semantics. It NEVER
converts a reading, touches the resolver/expected math, ingestion, rollups, the
scheduler, baselines, ``expected_weather_provenance``, or O&M. Producing or
comparing a fingerprint changes nothing — it only describes.

Why these fields (and not others): a declaration says "THIS device's THIS stream,
sourced THIS way, MEANS POA / cell / etc." If the device is re-pointed to a
different provider account/device, or its provider/source identity changes, the
declared meaning may no longer hold and a human should re-confirm it. Noisy,
non-identity fields (display name, timestamps, mapped_status, health/readiness, the
derived eligibility narrative) are deliberately EXCLUDED so benign churn never
produces a false "stale" signal. Blank/whitespace-only values are normalized to
``None`` so an absent value never reads as a change against another absent value.
"""
from __future__ import annotations

from typing import Any, Optional

# Bump ONLY when the fingerprint SHAPE changes. The comparator ignores this key so
# a pure schema migration never, by itself, flags an existing declaration stale.
FINGERPRINT_SCHEMA_VERSION = 1


def _norm(value: Any) -> Any:
    """Normalize a value for stable comparison.

    Enums collapse to their ``.value``; blank/whitespace-only strings become
    ``None`` (so absent == absent); all other scalars pass through unchanged.
    """
    v = getattr(value, "value", value)
    if v is None:
        return None
    if isinstance(v, str):
        return v.strip() or None
    return v


def compute_upstream_fingerprint(device: Any, mapping: Any) -> dict[str, Any]:
    """Build the deterministic upstream fingerprint for a declaration.

    ``mapping`` supplies the governed stream identity; ``device`` (may be ``None``
    for an external-only declaration) supplies the live telemetry link and stable
    descriptors. Pure: no DB access, no writes. ``getattr`` is used throughout so a
    ``None`` device (or a missing attribute) yields ``None`` rather than raising.
    The result is a plain JSON-serializable dict suitable for persisting in
    ``weather_device_mappings.upstream_fingerprint_json``.
    """
    telemetry_link = getattr(device, "telemetry_mapping", None)

    return {
        "schema_version": FINGERPRINT_SCHEMA_VERSION,
        # --- Governed stream identity (from the mapping itself) --------------
        "metric": _norm(getattr(mapping, "metric", None)),
        "provider_key": _norm(getattr(mapping, "provider_key", None)),
        "external_device_id": _norm(getattr(mapping, "external_device_id", None)),
        "weather_source_id": _norm(getattr(mapping, "weather_source_id", None)),
        "sensor_model": _norm(getattr(mapping, "sensor_model", None)),
        # --- Stable device descriptors --------------------------------------
        "device_category": _norm(getattr(device, "category", None)),
        "device_type": _norm(getattr(device, "type", None)),
        "device_role": _norm(getattr(device, "device_role", None)),
        "source_provider": _norm(getattr(device, "source_provider", None)),
        "external_device_type": _norm(getattr(device, "external_device_type", None)),
        # --- Live device->provider telemetry link (re-pointing == change) ----
        "link_provider_account_id": _norm(
            getattr(telemetry_link, "provider_account_id", None)
        ),
        "link_telemetry_device_id": _norm(
            getattr(telemetry_link, "telemetry_device_id", None)
        ),
    }


def compare_fingerprint(
    stored: Optional[dict[str, Any]], current: dict[str, Any]
) -> dict[str, Any]:
    """Compare a stored fingerprint to the current one (pure, never writes).

    Returns ``{"diverged": bool, "changed_keys": list[str], "summary": str|None}``.

    A missing/empty ``stored`` fingerprint means there is NO baseline to compare
    against, so divergence is ``False`` — a declaration is never flagged stale
    without a captured baseline (fail-safe: silence over a false positive). The
    ``schema_version`` key is ignored so a shape migration alone never diverges.
    ``changed_keys`` is sorted for a stable, deterministic summary.
    """
    if not stored:
        return {"diverged": False, "changed_keys": [], "summary": None}

    keys = (set(stored) | set(current)) - {"schema_version"}
    changed = sorted(k for k in keys if stored.get(k) != current.get(k))
    if not changed:
        return {"diverged": False, "changed_keys": [], "summary": None}

    summary = (
        "Upstream device identity changed since this declaration was made "
        f"({', '.join(changed)}); re-confirm the declared weather semantics."
    )
    return {"diverged": True, "changed_keys": changed, "summary": summary}
