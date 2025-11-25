import logging

from app.static.due_diligence_to_assets_keys_mapper import SITE_CARDS_FIELD_TO_DD_FIELDS_MAPPER

logger = logging.getLogger(__name__)


def get_site_cards_with_dd_data(site):
    """Map results from document keys to site schema fields"""
    site_cards = {}
    for card_name, documents in SITE_CARDS_FIELD_TO_DD_FIELDS_MAPPER.items():
        site_cards[card_name] = {}
        for document_name, fields_mappings in documents.items():
            document = site.get_document(document_name)
            for field_mapping in fields_mappings:
                site_schema_filed_name, due_diligence_key = field_mapping
                try:
                    dd_value = [key.value for key in document.keys if key.name == due_diligence_key][0]
                    site_cards[card_name][site_schema_filed_name] = dd_value
                except IndexError:
                    logger.warning(f"There is no value for key `{due_diligence_key}` in due diligence results")
                    site_cards[card_name][site_schema_filed_name] = None
    return site_cards
