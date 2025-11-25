from app.settings import settings
from app.static.files import FILE_PREVIEW_CONTENT_TYPE_MAPPING

TEST_FILE_NAME = "test_file.pdf"

INVALID_PREVIEW_FILE_EXTENSION_ERR_MSG = (
    f"Only {', '.join(FILE_PREVIEW_CONTENT_TYPE_MAPPING)} files are available to preview."
)

ALLOWED_FILE_EXTENSIONS = ", ".join(settings.allowed_extensions)
