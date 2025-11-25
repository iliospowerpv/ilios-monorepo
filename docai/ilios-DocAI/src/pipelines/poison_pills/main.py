import pandas as pd

from src.pipelines.poison_pills.base import PoisonPillsPipeline


def main() -> None:
    # file_paths = [
    #     "gs://doc_ai_storage/site-lease/documents/Brixmor-Blue Sky Felicita
    #     Plaza Lease - 7_17_19 (BSU Sig_ Deed Included).pdf",
    # ]
    # project_preview_builder = ProjectPreviewBuilder(
    #     file_paths,  # type: ignore
    #     agreement_type=AgreementType.SITE_LEASE,
    #     poison_pills_detection=True,
    # )
    # result = project_preview_builder.get_project_preview()
    # result.to_csv("output_ppills.csv")
    pipeline = PoisonPillsPipeline()
    result = pipeline.run(pd.read_csv("output_ppills.csv"))
    result.to_csv("output_ppills_final.csv")


if __name__ == "__main__":
    main()
