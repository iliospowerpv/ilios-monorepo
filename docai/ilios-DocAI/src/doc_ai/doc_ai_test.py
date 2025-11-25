import logging.config
import os

from src.doc_ai.file import File
from src.doc_ai.processor import DocAIProcessor


logging.config.fileConfig("logging.conf", disable_existing_loggers=False)
logger = logging.getLogger(__name__)


def main() -> None:
    """Run the DocAIProcessor example."""
    logger.info("Starting DocAIProcessor")
    processor = DocAIProcessor(
        location=os.environ["DOC_AI_LOCATION"],
        project_id=os.environ["PROJECT_ID"],
        processor_id=os.environ["DOC_AI_PROCESSOR_ID"],
    )
    file: File = processor.process_document(
        file_path="data/documents/Site Lease - Shine - DuQuoin.pdf"
    )
    # you can get a full Dict of paragraphs by calling doc_sequence.get_paragraphs()
    paragraph_dict = file.get_paragraphs()

    # print paragraphs on page 1
    logger.info(f"Extracted paragraphs from the first page: \n\n {paragraph_dict[1]}")
    logger.info("Finished DocAIProcessor")


if __name__ == "__main__":
    main()
