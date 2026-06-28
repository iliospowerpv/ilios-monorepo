"""Third-party weather provider adapter framework (Phases A–D).

This package mirrors ``app/integrations/telemetry`` for weather providers. It is
deliberately decoupled from ``app.models``: adapters speak in plain strings for
measurement semantics (``"ghi"``, ``"ambient"``, ...) and the import service
validates those strings against the model enums — exactly as the historical
import service already does for file/manual rows.

Context-only by construction: an adapter NEVER claims an external source is
physics-/expected-eligible. External GHI/ambient is stored verbatim and surfaced
as context, never transposed to POA or converted to cell temperature.
"""
