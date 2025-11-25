# flake8: noqa

define_risks = """Act as a lawyer or legal advisor reviewing a legal document. Indentify potential risks and issues in the document. Provide a summary of the risks and issues identified in the provided document. 
Return output in JSON format with keys: "risks" (string).
{{
    provided document: {document}
}}
"""

summarize_document = """Summarize the provided document in few sentences. Keep the key entities, keywords and topics. Return a summary of the document in JSON format with keys: "summary" (string).
{{
    provided document: {document}
}}
"""

extract_keywords = """Extract the keywords, entities, places, addresses and key topics from the provided document. Focus on the most important aspects from the view of a legal professional / lawyer. Return the keywords in JSON format with keys: "keywords" (list of strings).
{{
    provided document: {document}
}}
"""
