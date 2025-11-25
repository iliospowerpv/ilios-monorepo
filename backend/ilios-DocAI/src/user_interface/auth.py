import hmac
import os

import streamlit as st
from google.cloud import secretmanager


def check_password() -> bool:
    """Returns `True` if the user had the correct password."""

    def password_entered() -> None:
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(
            st.session_state["password"],
            get_secret(os.environ["PROJECT_ID"], "ui-password-webapp-integration"),
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Return True if the password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password.
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


def get_secret(project_id: str, secret_id: str, version_id: str = "latest") -> str:
    """Access the secret version and return the payload data."""
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version.
    response = client.access_secret_version(request={"name": name})

    # Return the payload data.
    return response.payload.data.decode("UTF-8")
