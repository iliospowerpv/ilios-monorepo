from google.cloud import secretmanager


def access_secret(project_id: str, secret_name: str, version_id: str | None = None) -> str:
    client = secretmanager.SecretManagerServiceClient()
    secret_id = f"projects/{project_id}/secrets/{secret_name}/versions/{version_id or "latest"}"
    response = client.access_secret_version(name=secret_id)
    return response.payload.data.decode("utf-8")
