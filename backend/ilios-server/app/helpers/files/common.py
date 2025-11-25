from fastapi import HTTPException, status


def validate_file_extension(filename, allowed_extensions):
    """"""
    *_, file_extension = filename.split(".")
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"File {filename} has invalid extension. Only {', '.join(allowed_extensions)} are allowed",
        )
    return filename
