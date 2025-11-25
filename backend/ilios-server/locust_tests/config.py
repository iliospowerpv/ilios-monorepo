from dotenv import dotenv_values


def load_secrets():  # noqa: FNE004
    return dotenv_values(".env-locust", verbose=True)


locust_secrets = load_secrets()
