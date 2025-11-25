from unittest.mock import Mock, patch

import pandas as pd
import pytest

from src.pipelines.constants import AgreementType
from src.pipelines.sql_retriever.base import ProjectPreviewRetriever


def get_llm_mock() -> Mock:
    llm = Mock()
    llm.batch.return_value = [Mock(content="Interconnection Agreement")]
    llm.invoke.return_value = Mock(content="Interconnection Agreement")
    return llm


@pytest.fixture
def project_preview_retriever() -> ProjectPreviewRetriever:
    """Create a mock ProjectPreviewRetriever object."""
    project_preview_retriever = ProjectPreviewRetriever(1)

    sql_connection = Mock()
    sql_connection.get_project_preview_values.return_value = pd.DataFrame(
        {
            "Key Items": ["item1", "item2"],
            "Value": ["value1", "value2"],
        }
    )

    project_preview_retriever.sql_connector = sql_connection
    return project_preview_retriever


def test_init() -> None:
    """Test the initialization of the ProjectPreviewRetriever class."""
    project_preview_retriever = ProjectPreviewRetriever(1)
    assert project_preview_retriever.site_id == 1


@patch("src.pipelines.sql_retriever.base.get_llm")
def test_get_agreement_type(
    mock_get_llm: Mock, project_preview_retriever: ProjectPreviewRetriever
) -> None:
    """Test that the get_agreement_type method returns a list of agreement types."""
    mock_get_llm.return_value = get_llm_mock()

    questions = ["What is the agreement type?"]
    agreement_types = project_preview_retriever.get_agreement_type(questions)
    assert isinstance(agreement_types, list)
    assert all(isinstance(item, str) for item in agreement_types)


def test_get_key_items(project_preview_retriever: ProjectPreviewRetriever) -> None:
    """Test that the get_key_items method returns a string."""
    project_preview_retriever.get_llm_key_items = (  # type: ignore
        lambda key_items_prompt: get_llm_mock()
    )
    question = "What are the key items?"
    available_key_items = ["item1", "item2"]
    key_items = project_preview_retriever.get_key_items(question, available_key_items)
    print(key_items)
    assert isinstance(key_items, str)


@patch("src.pipelines.sql_retriever.sql_connection.SQLConnector")
def test_get_project_preview_values(
    mock_SQLConnector: Mock, project_preview_retriever: ProjectPreviewRetriever
) -> None:
    """Test that the get_project_preview_values method returns a dataframe."""
    mock_SQLConnector.get_project_preview_values.return_value = pd.DataFrame()
    project_preview_retriever.sql_connector = mock_SQLConnector
    agreement_type = "Interconnection Agreement"
    project_preview_values = project_preview_retriever.get_project_preview_values(
        agreement_type
    )
    assert isinstance(project_preview_values, pd.DataFrame)


def test_get_data_user_prompt(
    project_preview_retriever: ProjectPreviewRetriever,
) -> None:
    """Test that the get_data_user_prompt method returns a tuple."""
    dataset = pd.DataFrame(
        [
            (
                "Who is responsible for the maintenance and repairs of the solar panels after installation?",  # noqa
                AgreementType.OM_AGREEMENT.value,
            ),
            (
                "What are the terms of energy price per kilowatt-hour for the next 10 years?",  # noqa
                AgreementType.PPA.value,
            ),
            (
                "What conditions must be met for connecting the solar power system to the local utility grid?",  # noqa
                AgreementType.INTERCONNECTION_AGREEMENT.value,
            ),
            (
                "What are the rights and obligations regarding the land where the solar farm is located?",  # noqa
                AgreementType.SITE_LEASE.value,
            ),
            (
                "What terms are outlined for managing the subscriptions and billing for community solar members?",  # noqa
                AgreementType.SUBSCRIBER_MANAGEMENT_AGREEMENT.value,
            ),
            (
                "What provisions govern the operational control of the solar facility by the project owners in operating agreement?",  # noqa
                AgreementType.OPERATING_AGREEMENT.value,
            ),
            (
                "What financial terms are in place to secure funding for the solar project?",  # noqa
                AgreementType.LOAN_AGREEMENT.value,
            ),
            (
                "What environmental conditions and site assessments are required before starting construction?",  # noqa
                AgreementType.PHASE_1_ESA.value,
            ),
        ],
        columns=["prompt", "expected"],
    )

    agreement_type = project_preview_retriever.get_agreement_type(
        dataset["prompt"].tolist()
    )
    assert isinstance(agreement_type, list)
    assert agreement_type == dataset["expected"].tolist()
