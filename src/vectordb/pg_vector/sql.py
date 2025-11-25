# flake8: noqa

retriever_sql = """
WITH semantic_search AS (
    SELECT id, RANK () OVER (ORDER BY summary_embedding <=> :embedding ::vector) AS rank
    FROM document_embeddings
    WHERE company_id = :company_id AND site_id = :site_id AND agreement_type = :agreement_type
    ORDER BY summary_embedding <=> :embedding ::vector
    LIMIT 10
),
keyword_search AS (
    SELECT id, RANK () OVER (ORDER BY ts_rank_cd(to_tsvector('english', content), query) DESC)
    FROM document_embeddings, plainto_tsquery('english', :query ) query
    WHERE to_tsvector('english', content) @@ query AND company_id = :company_id AND site_id = :site_id AND agreement_type = :agreement_type
    ORDER BY ts_rank_cd(to_tsvector('english', content), query) DESC
    LIMIT 10
)
SELECT
    COALESCE(semantic_search.id, keyword_search.id) AS id,
    COALESCE(1.0 / ( :k + semantic_search.rank), 0.0) +
    COALESCE(1.0 / ( :k + keyword_search.rank), 0.0) AS score,
    document_embeddings.content as content,
    document_embeddings.agreement_type as agreement_type,
     document_embeddings.section_name as section_name,
      document_embeddings.subsection_name as subsection_name,
       document_embeddings.document_name as document_name,
        document_embeddings.file_name as file_name
FROM semantic_search
FULL OUTER JOIN keyword_search ON semantic_search.id = keyword_search.id
JOIN document_embeddings ON semantic_search.id = document_embeddings.id
ORDER BY score DESC
LIMIT 5
"""


retriever_sql_by_document_name = """
WITH semantic_search AS (
    SELECT id, RANK () OVER (ORDER BY summary_embedding <=> :embedding ::vector) AS rank
    FROM document_embeddings
    WHERE company_id = :company_id AND site_id = :site_id AND document_name = :document_name
    ORDER BY summary_embedding <=> :embedding ::vector
    LIMIT 10
),
keyword_search AS (
    SELECT id, RANK () OVER (ORDER BY ts_rank_cd(to_tsvector('english', content), query) DESC)
    FROM document_embeddings, plainto_tsquery('english', :query ) query
    WHERE to_tsvector('english', content) @@ query AND company_id = :company_id AND site_id = :site_id AND document_name = :document_name
    ORDER BY ts_rank_cd(to_tsvector('english', content), query) DESC
    LIMIT 10
)
SELECT
    COALESCE(semantic_search.id, keyword_search.id) AS id,
    COALESCE(1.0 / ( :k + semantic_search.rank), 0.0) +
    COALESCE(1.0 / ( :k  + keyword_search.rank), 0.0) AS score,
    document_embeddings.content as content,
    document_embeddings.agreement_type as agreement_type,
     document_embeddings.section_name as section_name,
      document_embeddings.subsection_name as subsection_name,
       document_embeddings.document_name as document_name,
        document_embeddings.file_name as file_name
FROM semantic_search
FULL OUTER JOIN keyword_search ON semantic_search.id = keyword_search.id
JOIN document_embeddings ON semantic_search.id = document_embeddings.id
ORDER BY score DESC
LIMIT 5
"""

insert_sql = """
    INSERT INTO document_embeddings (file_id, site_name, site_id, company_name, company_id, agreement_type, document_name, file_name, section_name, subsection_name, keywords, risks, summary, summary_embedding, document, content, embedding, actual) 
    VALUES ( :file_id, :site_name, :site_id, :company_name, :company_id, :agreement_type, :document_name, :file_name, :section_name, :subsection_name, :keywords, :risks, :summary, :summary_embedding ::vector, :document, :content, :embedding ::vector, :actual)
"""

insert_sql_chatbot_history = """
    INSERT INTO chatbot_history (
    conversation_id, user_id, company_id, site_id, message, message_type, message_index
) VALUES (
    %(conversation_id)s, %(user_id)s, %(company_id)s, %(site_id)s, %(message)s, %(message_type)s, %(message_index)s
)
"""
