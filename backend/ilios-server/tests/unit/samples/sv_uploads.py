from unittest.mock import ANY

TEST_SITE_VISIT_UPLOAD_NAME = "image.png"

TEST_SV_UPLOAD_GEN_UPLOAD_LINK_VALID_PAYLOAD = {"filename": TEST_SITE_VISIT_UPLOAD_NAME}
TEST_SV_UPLOAD_GEN_UPLOAD_LINK_WRONG_PAYLOAD = {"filename": "attachment.pdf"}

TEST_SV_UPLOAD_TRACK_UPLOAD_VALID_PAYLOAD = {"filename": TEST_SITE_VISIT_UPLOAD_NAME, "filepath": "path/to/image.png"}

TEST_SV_UPLOAD_ITEM = {
    "id": ANY,
    "author": "Deleted User",
    "filename": TEST_SITE_VISIT_UPLOAD_NAME,
    "extension": "png",
    "created_at": ANY,
}


TEST_SV_UPLOAD_INVALID_EXTENSION_ERR = "File attachment.pdf has invalid extension. Only jpeg, jpg, png are allowed"
