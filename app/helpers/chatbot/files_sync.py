from app.helpers.cloud_function_client import AIServerClient
from app.settings import settings


class ChatBotFilesSyncer:
    """Implements API calls for AI to sync DD files between storages"""

    @staticmethod
    def upload_file(payload):
        """Let ChatBot knows about new file uploading to add it to the vector storage"""
        client = AIServerClient(func_url=settings.chatbot_upload_file_function_url)
        client.post(payload=payload, use_api_key=True)

    @staticmethod
    def mark_file_actual(params):
        """Let ChatBot knows about changing file actuality status to prioritize this file content usage"""
        client = AIServerClient(func_url=settings.chatbot_mark_actual_function_url)
        client.post(params=params, use_api_key=True)

    @staticmethod
    def delete_file(params):
        """Let ChatBot knows about file removal to delete it to the vector storage"""
        client = AIServerClient(func_url=settings.chatbot_delete_file_function_url)
        client.post(params=params, use_api_key=True)
