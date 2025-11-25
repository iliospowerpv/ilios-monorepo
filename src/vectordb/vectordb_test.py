from unittest.mock import Mock

from src.vectordb.vectordb import VectorDB


if __name__ == "__main__":
    text = open("site-lease-example.txt").read()

    vectordb = VectorDB()
    file_sequence = Mock()
    file_sequence.get_all_text.return_value = text
    file_sequence.get_tables.return_value = []
    file_sequence.get_form_fields.return_value = []
    retriever = vectordb.retriever_from_file_sequence(file_sequence)

    query = (
        "Tenant may extend the Initial Term"
        " for three (3) additional five (5) years periods"
    )
    for doc in retriever.get_relevant_documents(query):
        print(doc.page_content)
        print("-------------------------------------------------------------------\n\n")
