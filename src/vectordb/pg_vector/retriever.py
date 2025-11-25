from typing import Any, Dict, List

from langchain.schema import Document

from src.embeddings.vertex import VertexAIEmbedder
from src.pipelines.constants import AgreementType
from src.vectordb.pg_vector.config import PGVectorConfig
from src.vectordb.pg_vector.connector import PGVectorConnector
from src.vectordb.pg_vector.sql import retriever_sql, retriever_sql_by_document_name


class PGVectorRetriever:
    """Class used to retrieve documents from the PGVector index."""

    def __init__(self, config: PGVectorConfig) -> None:
        self.config = config
        self.db_connector = PGVectorConnector(config)
        self.embedder: VertexAIEmbedder = VertexAIEmbedder()

    def get_documents(
        self,
        query: str,
        filters: Dict[str, Any],
    ) -> List[Document]:
        """Get a relevant document from the PGVector index based on query and filters.
        Example query
        get_documents("Who is the landlord of the Land lease agreement?",
        filters={'k': k, 'company_id': 1, 'site_id': 1, 'agreement_type': 'Site Lease'})
        """

        query_embedding = self.embedder.get_single_embedding(
            query, embeddings_task_type="RETRIEVAL_QUERY"
        )
        filters["embedding"] = query_embedding
        filters["query"] = query
        if filters.get("document_name") is not None:
            retriever_sql_adjusted = retriever_sql_by_document_name[::]
        else:
            retriever_sql_adjusted = retriever_sql[::]

        result = self.db_connector.execute_retrieval_query(
            retriever_sql_adjusted, filters
        )
        return [
            Document(
                page_content=document_tuple[2],
                metadata={
                    "agreement_type": document_tuple[3],
                    "section_name": document_tuple[4],
                    "subsection_name": document_tuple[5],
                    "document_name": document_tuple[6],
                    "file_name": document_tuple[7],
                },
            )
            for document_tuple in result
        ]

    def get_risks(self, filters: Dict[str, Any]) -> List[Document]:
        """Pass company_id, site_id, and agreement_type to get risks."""

        where_clause = " AND ".join([f"{key} = :{key} " for key in filters.keys()])

        query = f"""SELECT risks, agreement_type, section_name,
                 subsection_name, document_name, file_name
                 FROM {self.config.chatbot_documents_table_name} 
                 WHERE {where_clause}"""

        result = self.db_connector.execute_retrieval_query(query, filters)
        return [
            Document(
                page_content=document_tuple[0],
                metadata={
                    "agreement_type": document_tuple[1],
                    "section_name": document_tuple[2],
                    "subsection_name": document_tuple[3],
                    "document_name": document_tuple[4],
                    "file_name": document_tuple[5],
                },
            )
            for document_tuple in result
            if document_tuple[0]
        ]

    def get_other_agreement_type_document_names(
        self, site_id: int, company_id: int
    ) -> Any:
        query = f"""SELECT DISTINCT document_embeddings.document_name 
        FROM document_embeddings 
        WHERE site_id = {site_id} 
        AND company_id = {company_id}
        AND agreement_type = '{AgreementType.OTHER.value}';"""
        return self.db_connector.execute_query(query)
