from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, TEXT, Boolean, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()
N_DIM = 768


class DocumentModel(Base):  # type: ignore
    __tablename__ = "document_embeddings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(Integer)
    site_name = Column(String)
    site_id = Column(Integer)
    company_name = Column(String)
    company_id = Column(Integer)
    agreement_type = Column(String)
    document = Column(String)
    embedding = Vector(N_DIM)
    summary = Column(String)
    summary_embedding = Vector(N_DIM)
    content = Column(String)
    keywords = Column(ARRAY(TEXT))  # type: ignore
    risks = Column(String)
    actual = Column(Boolean, default=False)
