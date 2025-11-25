import pandas as pd

from src.pipelines.constants import AgreementType
from src.pipelines.project_preview_builder import ProjectPreviewBuilder


def main() -> None:
    """Quick test of the main Key Value Extraction pipeline. It checks one EPC file for
    correct run"""
    file_url = (
        "gs://doc_ai_storage/epc/documents/EPC - Blue Sky - Felicita Town Center.pdf"
    )
    agreement_type = AgreementType.EPC
    detect_poison_pills = True

    pp_builder = ProjectPreviewBuilder(
        file_paths=[file_url],
        agreement_type=agreement_type,
        poison_pills_detection=detect_poison_pills,
    )
    pp_dict = pp_builder.get_project_preview_dict()
    pandas_df = pd.DataFrame.from_dict(pp_dict, orient="columns")
    pandas_df.to_csv("project_preview_example_epc.csv", index=False)


if __name__ == "__main__":
    main()
