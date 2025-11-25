from typing import List, Optional

from src.pipelines.mappings import agreement_type_to_config


agreement_types_key_items = {
    agreement_type.value: config().get_terms_and_definitions()["Key Items"].tolist()
    for agreement_type, config in agreement_type_to_config.items()
}


def get_agreement_types_key_items_str(
    other_agreement_type_document_names: List[str],
) -> str:
    agreement_types_with_key_items = "\n".join(
        f"{k}: [{', '.join(v)}]" for k, v in agreement_types_key_items.items()
    )

    ans = f"""Agreement Types without Key Items: [{other_agreement_type_document_names}]
Agreement Types with Key Items (Agreement Type: [Key Items]):{agreement_types_with_key_items}"""  # noqa: E501

    return ans


def sources_string(
    section_name: str,
    document_name: str,
    file_name: str,
    sub_section_name: Optional[str] = None,
) -> str:

    ans = (
        f"Section name: {section_name}\n"
        + (f"Sub-section name: {sub_section_name}\n" if sub_section_name else "")
        + f"Document name: {document_name}\n"
        + f"File name: {file_name}\n"
    )

    return ans


def doc_string_template(
    source_type: str,
    section_name: str,
    document_name: str,
    file_name: str,
    sub_section_name: Optional[str] = None,
) -> str:
    return f"Source type: {source_type}\n" + sources_string(
        section_name, document_name, file_name, sub_section_name
    )
