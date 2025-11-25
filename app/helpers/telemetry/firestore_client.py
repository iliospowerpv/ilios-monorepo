from google.cloud import firestore
from google.oauth2 import service_account

from app.firestore_models.firestore_company_config import FSCompanyConfig
from app.settings import settings


class FirestoreClient:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(settings.service_account_key_file_path)
        self.db = firestore.Client(
            credentials=credentials, project=settings.telemetry_project_name, database=settings.firestore_db_name
        )
        # Collection name depends on environment
        collection_name = f"{settings.environment_name}-{settings.telemetry_config_collection_name}"
        self.config_collection = self.db.collection(collection_name)

    def get_company_config(self, company_id: int) -> FSCompanyConfig | None:
        document_name = f"company-{company_id}"
        doc_ref = self.config_collection.document(document_name)
        company_config_dict = doc_ref.get().to_dict()
        if company_config_dict:
            return FSCompanyConfig.from_dict(company_config_dict)

    def create_company_config(self, fs_company: FSCompanyConfig):
        document_name = f"company-{fs_company.id}"
        self.config_collection.document(document_name).set(fs_company.to_dict())

    def update_company_config(self, fs_company: FSCompanyConfig):
        document_name = f"company-{fs_company.id}"
        doc_ref = self.config_collection.document(document_name)
        doc_ref.set(fs_company.to_dict())

    def delete_company_config(self, company_id: int):
        document_name = f"company-{company_id}"
        self.config_collection.document(document_name).delete()
