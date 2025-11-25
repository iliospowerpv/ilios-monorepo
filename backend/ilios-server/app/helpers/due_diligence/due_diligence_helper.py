from sqlalchemy.orm import Session

from app.crud.document_section import DocumentSectionCRUD
from app.crud.site import SiteCRUD
from app.helpers.due_diligence.document_section_mapper import document_name_section_mapper, document_sub_sections_mapper


def generate_default_site_documents(
    site_ids: [] = None, db_session: Session = None, document_mapper: list = document_name_section_mapper
) -> []:
    """Generate default site documents structure with all possible sections and document types.

    :param site_ids: list of site ids
    :param db_session: database session
    :param document_mapper: list mapping between  document names and document sections
    :return: list of default site documents e.g.: [{"site_id": 1, "section_name": "preview", "kind": "om_agreement"}]
    """
    sites_documents = []
    if site_ids is None:
        site_ids = [site.id for site in SiteCRUD(db_session).get(skip_pagination=True)]
    for site_id in site_ids:
        site_sections = {
            section.name: section.id for section in DocumentSectionCRUD(db_session).get_site_sections(site_id=site_id)
        }
        for section_name, section_documents in document_mapper.items():
            section_id = site_sections.get(section_name)
            # use enumerate to set documents to the specific position in the section
            for section_document_position, section_document in enumerate(section_documents, start=1):
                sites_documents.append(
                    {
                        "site_id": site_id,
                        "section_id": section_id,
                        "name": section_document.name,
                        "position": section_document_position,
                    }
                )
    return sites_documents


def create_default_site_document_sections(
    site_ids: [] = None, db_session: Session = None, sub_sections_mapper: list = document_sub_sections_mapper
):
    top_level_sections = sub_sections_mapper.keys()
    section_crud = DocumentSectionCRUD(db_session)
    if site_ids is None:
        site_ids = [site.id for site in SiteCRUD(db_session).get(skip_pagination=True)]
    for site_id in site_ids:
        # using 'enumerate' we set sections/subsections in the strict order
        for top_section_position, top_section in enumerate(top_level_sections, start=1):
            top_section_id = section_crud.create_item(
                {"site_id": site_id, "name": top_section.name, "position": top_section_position}
            ).id
            subsections_list = [
                {
                    "site_id": site_id,
                    "name": section.name,
                    "parent_section_id": top_section_id,
                    "position": section_position,
                }
                for section_position, section in enumerate(sub_sections_mapper.get(top_section), start=1)
            ]
            section_crud.create_items(subsections_list)


def drop_default_site_document_sections(site_ids: [] = None, db_session: Session = None):
    if site_ids is None:
        site_ids = [site.id for site in SiteCRUD(db_session).get(skip_pagination=True)]
    DocumentSectionCRUD(db_session).drop_site_default_sections(site_ids)


def validate_document_section(document_name: str, section_id: int, db_session: Session):
    section_name = DocumentSectionCRUD(db_session).get_by_id(section_id).name
    section_documents = document_name_section_mapper.get(section_name)
    if document_name not in section_documents:
        valid_input = ", ".join([f"'{i.value}'" for i in section_documents])
        raise ValueError(
            f"There is no '{document_name.value}' documents in '{section_name.value}' document section. "
            f"Input should be one of: {valid_input}"
        )
