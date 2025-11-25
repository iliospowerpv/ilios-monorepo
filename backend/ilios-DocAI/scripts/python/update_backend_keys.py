"""
- https://backend-dot-prj-qa-base-23d1.uc.r.appspot.com/docs
- https://backend-dot-prj-dev-base-e61d.uw.r.appspot.com/docs
- https://backend-dot-prj-uat-base-70ab.uc.r.appspot.com/docs
"""
import json
import os
import pathlib
from typing import Any, List

import pandas as pd
import requests

from src.pipelines.constants import AgreementType
from src.pipelines.mappings import agreement_type_to_config
from src.settings import PROJECT_ROOT_PATH
from src.user_interface.auth import get_secret

API_KEY = get_secret(os.environ["PROJECT_ID"], "backend-api-key")
QA_INTERNAL_CONFIGS = get_secret(os.environ["PROJECT_ID"], "qa-internal-configs")


def get_key_items(pipeline_config: Any) -> List[str]:
    pipeline_folder = pathlib.Path(
        PROJECT_ROOT_PATH / f"src/pipelines/terms/{pipeline_config.pipeline_name}"
    )
    terms_and_instructions = pd.read_csv(pipeline_folder / "terms-instructions.csv")
    return terms_and_instructions["Key Items"].to_list()  # type: ignore


def get_name_mapping():
    return requests.get(
        QA_INTERNAL_CONFIGS,
        params={"config_type": "agreement_names", "api_key": API_KEY},  # type: ignore
    ).json()


def main():
    file_path = pathlib.Path(PROJECT_ROOT_PATH / "scripts/ai_parsing.json")
    names_mapping = get_name_mapping()

    keys_list = {}
    for name, ai_name in names_mapping.items():
        try:
            keys_list[name] = get_key_items(
                agreement_type_to_config[AgreementType.from_str(ai_name)]()
            )
        except ValueError:
            print("Unsupported agreement type", name, ai_name)
    with open(file_path, "w") as f:
        json.dump(keys_list, f, indent=4)


if __name__ == '__main__':
    main()
