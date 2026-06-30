import { ASSISTANT_ENTRY_SOURCES } from '../assistantLauncher';

// Canonical assistant entry-source vocabulary, kept as an independent "golden" copy. The test fails
// if either the runtime tuple OR this pinned list changes, forcing a conscious update on both sides.
// It MUST stay byte-for-byte in sync with the backend `_ENTRY_SOURCES` allowlist in
// backend/ilios-server/app/services/assistant/ui_events_service.py (which has its own mirror test in
// tests/test_assistant_analytics.py). This is the cross-language drift guard for the
// `discoverability_entry_clicked` analytics event.
const CANONICAL_ENTRY_SOURCES = ['empty_state', 'help_menu', 'module_header', 'sidebar', 'topbar'];

describe('assistant entry-source vocabulary (drift guard)', () => {
  it('matches the canonical, backend-mirrored allowlist', () => {
    expect([...ASSISTANT_ENTRY_SOURCES].sort()).toEqual(CANONICAL_ENTRY_SOURCES);
  });

  it('has no duplicate tokens', () => {
    expect(new Set(ASSISTANT_ENTRY_SOURCES).size).toBe(ASSISTANT_ENTRY_SOURCES.length);
  });
});
