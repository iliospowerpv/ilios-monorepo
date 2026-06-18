"""Regression coverage for per-file-version scoping of accepted document keys.

Bug: ``combine_user_ai_parsing_results`` built the per-field accepted ``value``
from ``Document.keys`` (every key across every file version of the document)
instead of the file version actually being viewed. A newly uploaded file
version therefore *inherited* the previous version's accepted values, so the
"Accept All" button rendered the "Accepted" (completed) state even though
nothing on the new version had been accepted and no candidate facts existed
for it (leaving "Promote" correctly, but confusingly, unavailable).

The fix scopes the accepted keys to the current file version plus legacy
document-level (``file_id IS NULL``) keys, with file-specific keys overriding
legacy keys for the same field.

These are pure unit tests: the document type config lookups are monkeypatched
and lightweight stand-in objects feed controlled keys, so the test exercises
only the scoping logic and does not depend on the extraction registry being
seeded in the test database.
"""

from types import SimpleNamespace
from unittest.mock import Mock

from app.helpers.configs import ai_parsing_helper
from app.helpers.files.file_helper import combine_user_ai_parsing_results

FIELD_A = "Field A"
FIELD_B = "Field B"


def _key(name, value, file_id):
    return SimpleNamespace(
        name=name,
        value=value,
        file_id=file_id,
        updated_at=None,
        id=id(object()),
        is_poison_pill=False,
        poison_pill_notes=None,
    )


def _file(file_id):
    return SimpleNamespace(id=file_id, latest_ai_result=None)


class TestFileVersionScoping:
    @staticmethod
    def _patch_config(monkeypatch):
        config = {
            "fields": [
                {"name": "field_a", "display_name": FIELD_A},
                {"name": "field_b", "display_name": FIELD_B},
            ]
        }
        monkeypatch.setattr(ai_parsing_helper.AIParsingHandler, "__init__", lambda self, db_session: None)
        monkeypatch.setattr(
            ai_parsing_helper.AIParsingHandler, "get_extraction_config", lambda self, document_type: config
        )
        monkeypatch.setattr(
            ai_parsing_helper.AIParsingHandler,
            "get_keys_by_document_type",
            lambda self, document_type: [FIELD_A, FIELD_B],
        )

    @staticmethod
    def _by_name(keys):
        return {key["name"]: key for key in keys}

    def test_new_version_does_not_inherit_old_version_accepted_values(self, monkeypatch):
        self._patch_config(monkeypatch)
        old_file, new_file = _file(1), _file(2)
        # FIELD_A accepted only on the OLD version; a legacy NULL-file key on FIELD_B.
        document = SimpleNamespace(
            name=SimpleNamespace(value="site_lease"),
            keys=[
                _key(FIELD_A, "Old Version Accepted Value", file_id=old_file.id),
                _key(FIELD_B, "Legacy Document Level Value", file_id=None),
            ],
        )

        new_view = self._by_name(
            combine_user_ai_parsing_results(document=document, due_diligence_file=new_file, db_session=Mock())
        )

        # The old version's accepted value must NOT leak into the new version.
        assert new_view[FIELD_A].get("value") is None
        # Legacy document-level (NULL file_id) keys must still surface.
        assert new_view[FIELD_B].get("value") == "Legacy Document Level Value"

    def test_old_version_shows_its_values_and_file_keys_override_legacy(self, monkeypatch):
        self._patch_config(monkeypatch)
        old_file = _file(1)
        document = SimpleNamespace(
            name=SimpleNamespace(value="site_lease"),
            keys=[
                _key(FIELD_A, "Old Version Accepted Value", file_id=old_file.id),
                _key(FIELD_B, "Legacy Document Level Value", file_id=None),
                _key(FIELD_B, "Old Version Override Value", file_id=old_file.id),
            ],
        )

        old_view = self._by_name(
            combine_user_ai_parsing_results(document=document, due_diligence_file=old_file, db_session=Mock())
        )

        # The viewed version's own accepted value surfaces.
        assert old_view[FIELD_A].get("value") == "Old Version Accepted Value"
        # A file-specific key wins over a legacy document-level key for the same field.
        assert old_view[FIELD_B].get("value") == "Old Version Override Value"

    def test_without_a_file_all_document_keys_are_used(self, monkeypatch):
        """Back-compat: when no file is provided, behavior is unchanged (all keys)."""
        self._patch_config(monkeypatch)
        document = SimpleNamespace(
            name=SimpleNamespace(value="site_lease"),
            keys=[
                _key(FIELD_A, "Some Value", file_id=99),
                _key(FIELD_B, "Legacy Value", file_id=None),
            ],
        )

        view = self._by_name(combine_user_ai_parsing_results(document=document, db_session=Mock()))

        assert view[FIELD_A].get("value") == "Some Value"
        assert view[FIELD_B].get("value") == "Legacy Value"
