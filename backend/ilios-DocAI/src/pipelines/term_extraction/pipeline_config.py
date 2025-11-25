import dataclasses
import logging
import os
import pathlib
from typing import List, Optional, Sequence

import pandas as pd
from pydantic import model_validator
from pydantic.dataclasses import dataclass

from src import settings
from src.doc_ai.processors import DOC_AI_PROCESSOR
from src.pipelines.constants import NOT_PROVIDED_STR
from src.pipelines.term_extraction.utils import (
    get_project_preview,
    get_terms_and_definitions,
    get_terms_and_instructions,
)


logger = logging.getLogger(__name__)


@dataclass
class PipelineConfig:
    """Configuration for the term_extraction.
    This class is used to store the configuration for the term_extraction."""

    PROJECT_ROOT_PATH = pathlib.Path(os.environ["PWD"])
    DATA_FOLDER_PATH = PROJECT_ROOT_PATH / "data"
    GCS_BUCKET_PATH = settings.GCS_BUCKET_PATH
    OUTPUT_RESULTS_PATH = "output"

    project_previews_folder: str = "project-previews"
    documents_folder: str = "documents"
    model_type: str = "GEMINI15"
    use_gcs_storage: bool = True
    pipeline_name: Optional[str] = None
    document_type: Optional[str] = None
    k: int = 5
    chunk_size: Optional[int] = None
    overlap_factor: Optional[int] = None
    add_tables: bool = False
    few_shot: bool = False
    keys: List[str] = dataclasses.field(default_factory=list)

    processor_location: str = os.environ["DOC_AI_LOCATION"]
    processor_project_id: str = os.environ["PROJECT_ID"]
    processor_id: str = DOC_AI_PROCESSOR["PROCESSOR"]
    few_shot_file_names: Sequence[str] = dataclasses.field(default_factory=list)
    file_names: Sequence[str | Sequence[str]] = dataclasses.field(default_factory=list)

    metrics: List[str] = dataclasses.field(
        default_factory=lambda: [
            "llm_validation",
            "llm_validation_binary",
            "levenshtein_score",
            "bleu_score",
            "rougeL_f1_score",
            "meteor_score",
            "rouge1_f1_score",
            "rouge1_precision_score",
            "rouge1_recall_score",
            "rougeL_precision_score",
            "rougeL_recall_score",
        ]
    )

    def get_path(self, folder_name: str) -> str:
        """Get the path for a specific folder."""
        return f"{self.get_data_folder()}/{self.pipeline_name}/{folder_name}"

    def get_local_terms_path(self, file_name: str) -> str:
        """Get the local path."""
        return f"src/pipelines/terms/{self.pipeline_name}/{file_name}"

    def get_data_folder(self) -> str | pathlib.Path:
        return self.GCS_BUCKET_PATH if self.use_gcs_storage else self.DATA_FOLDER_PATH

    def get_documents_path(self) -> str:
        """Get the documents' path."""
        return self.get_path(f"{self.documents_folder}/")

    def get_project_previews_path(self) -> str:
        """Get the project previews path."""
        return self.get_path(f"{self.project_previews_folder}/")

    def get_terms_definitions_path(self) -> str:
        """Get the terms and definitions path."""
        return self.get_local_terms_path("terms-definitions.csv")

    def get_terms_instructions_path(self) -> str:
        """Get the terms and definitions path."""
        return self.get_local_terms_path("terms-instructions.csv")

    def get_terms_and_instructions(self) -> pd.DataFrame:
        """Load the terms and instructions from the csv file."""
        terms_and_instructions = pd.read_csv(self.get_terms_instructions_path())
        if self.keys:
            terms_and_instructions = terms_and_instructions[
                terms_and_instructions["Key Items"].isin(self.keys)
            ]
            logger.info(
                f"Using only the following keys: "
                f"{terms_and_instructions['Key Items'].unique()}"
            )
        return terms_and_instructions

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        terms_and_definitions = get_terms_and_definitions(
            self.get_terms_definitions_path()
        )
        if self.keys:
            terms_and_definitions = terms_and_definitions[
                terms_and_definitions["Key Items"].isin(self.keys)
            ]
            logger.info(
                f"Using only the following keys: "
                f"{terms_and_definitions['Key Items'].unique()}"
            )
        return terms_and_definitions

    def get_few_shot_examples(self) -> pd.DataFrame:
        """Get the few shot examples."""
        logging.info(f"Reading few shot examples for {self.pipeline_name}")
        if not self.few_shot or not self.get_few_shot_file_names():
            return pd.DataFrame()

        terms_and_definitions_keys = self.get_terms_and_definitions()["Key Items"]
        few_shot_examples = []
        for file_name in self.get_few_shot_file_names():
            correct_project_preview = get_project_preview(
                self.get_project_previews_path(), file_name
            ).set_index("Key Items")

            keys = list(
                set(correct_project_preview.index).intersection(
                    set(terms_and_definitions_keys)
                )
            )
            difference = set(correct_project_preview.index).symmetric_difference(
                set(keys)
            )
            if difference:
                logging.info(
                    f"Few shot examples should have the same keys"
                    f" as the terms and definitions. "
                    f"Check these keys: "
                    f"{difference}"
                )
            correct_project_preview = correct_project_preview.loc[keys, "Legal Terms"]

            correct_project_preview.name = file_name

            few_shot_examples.append(correct_project_preview)

        few_shot_examples = pd.concat(few_shot_examples, axis=1).fillna(
            NOT_PROVIDED_STR
        )
        return few_shot_examples

    @staticmethod
    def delete_extensions(file_names: Sequence[str]) -> List[str]:
        """Delete the extensions from the file names."""
        return list(map(lambda x: x[:-4], file_names))

    @model_validator(mode="after")  # type: ignore
    def check_few_shots(self) -> None:
        """Check if the few shot files are not overlapping with the file names."""
        overlapping_files = set(
            self.delete_extensions(self.get_few_shot_file_names())
        ).intersection(set(self.delete_extensions(self.get_all_files())))
        if overlapping_files:
            raise ValueError(
                "Few shot files should not be overlapping with the file names."
                f"Check these files: {list(overlapping_files)}"
            )

    def get_output_results_path(self) -> str:
        """Get the output results path."""
        return f"{self.OUTPUT_RESULTS_PATH}-{self.pipeline_name}.csv"

    def get_few_shot_file_names(self) -> Sequence[str]:
        """Get the few shot files."""
        return self.few_shot_file_names

    def get_file_names(self) -> Sequence[str | Sequence[str]]:
        """Get the file names."""
        return self.file_names

    def get_all_files(self) -> List[str]:
        """Get all the files."""
        return [
            item
            for sublist in self.file_names
            for item in (sublist if isinstance(sublist, list) else [sublist])
        ]


@dataclass
class SiteLeasePipelineConfig(PipelineConfig):
    """Configuration for the site lease term_extraction."""

    pipeline_name: str = "site-lease"
    project_previews_folder: str = (
        "project-previews-updated-enriched-and-not-provided-instr-fix"
    )
    chunk_size: int = 6000
    k: int = 5
    model_type: str = "CLAUDE"
    few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "Site Lease - GLD - Canton (ES).pdf",
            "Site Lease - SunRaise - Happy Hollow (ES).pdf",
            "Carmen.Site Lease.Blue Sky.pdf",
            "Caroline_SiteLease_Updated Ex 2_2018.12.31.pdf",
            "Site Green - Emerald Garden - Cape Fear.pdf",
        ]
    )
    short_terms_few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "Site Lease - GLD - Canton (ES).pdf",
            "Site Lease - SunRaise - Happy Hollow (ES).pdf",
            "Site Lease- SunRaise - Plympton.pdf",
            "Carmen.Site Lease.Blue Sky.pdf",
            "Caroline_SiteLease_Updated Ex 2_2018.12.31.pdf",
            "Site Green - Emerald Garden - Cape Fear.pdf",
            "Site Lease - Blue Sky- Felicita Town Center.pdf",
            "Site Lease - Bullrock - Lakeville.pdf",
            "Site Lease - Emerald Garden - Marshfield Mass.pdf",
            "Site Lease - Emerald Garden - Mt Kimble.pdf",
        ]
    )

    file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "Site Lease- SunRaise - Plympton.pdf",
            "Site Lease - Blue Sky- Felicita Town Center.pdf",
            "Site Lease - Bullrock - Lakeville.pdf",
            "Site Lease - Emerald Garden - Marshfield Mass.pdf",
            "Site Lease - Emerald Garden - Mt Kimble.pdf",
            "Site Lease - GLD - Hi Lo Biddy.pdf",
            "Site Lease - Neighborhood Power - Mt Hope.pdf",
            "Site Lease - Novel - Bartel (ES).pdf",
            "Site Lease - Novel - Shelly.pdf",
            "Site Lease - NPC - Williams Acres.pdf",
            "Site Lease - Shine - DuQuoin.pdf",
            "Site Lease - Shine - John A Logan (ES).pdf",
            "Site Lease - SunRaise - Enterprise Ave. Gardiner.pdf",
            "Site Lease - SunRaise - Pequawket.pdf",
            "Site Lease- SunRaise - Nutting Ridge.pdf",
        ]
    )

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        return self.get_terms_and_instructions()


@dataclasses.dataclass
class InterconnectionAgreementPipelineConfig(PipelineConfig):
    """Configuration for the interconnection agreement term_extraction."""

    pipeline_name: str = "interconnection-agreement"
    project_previews_folder: str = "project-previews-updated-updated-pp-v2"
    chunk_size: int = 6000
    k: int = 5
    model_type: str = "CLAUDE"
    few_shot_file_names: List[str] = dataclasses.field(default_factory=lambda: [])
    short_terms_few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "Blue Sky.Interconnection Agreement.Felicita Town Centre.pdf",
            "GLD.Interconnection Agreement.Canton.pdf",
            "Interconnection Agreement - Bullrock - Lakeville.pdf",
            "Interconnection Agreement - Emerald Green - Cape Fear.pdf",
            "Interconnection Agreement - Emerald Green - Mt Kimble BLDG A.pdf",
        ]
    )

    file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "Blue Sky.Interconnection Agreement.Felicita Town Centre.pdf",
            "GLD.Interconnection Agreement.Canton.pdf",
            "Interconnection Agreement - Bullrock - Lakeville.pdf",
            "Interconnection Agreement - Emerald Green - Cape Fear.pdf",
            "Interconnection Agreement - Emerald Green - Mt Kimble BLDG A.pdf",
            "Interconnection Agreement - Neighborhood Power - My Hope.pdf",
            "Interconnection Agreement - Novel - Bartel.pdf",
            "Signed IA - DuQuoin WWTP.pdf",
            "Interconnection Agreement - SunRaise - Pequawket Trail Baldwin.pdf",
            "Sunraise.Interconnection Agreement.Enterprise.pdf",
        ]
    )

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        return self.get_terms_and_instructions()


@dataclasses.dataclass
class PPAPipelineConfig(PipelineConfig):
    """Configuration for the power purchase agreement term_extraction."""

    pipeline_name: str = "ppa"
    project_previews_folder: str = "project-previews-false-positives-reviewed"
    chunk_size: int = 6000
    k: int = 5
    model_type: str = "CLAUDE"
    few_shot_file_names: List[str] = dataclasses.field(default_factory=lambda: [])

    short_terms_few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "Sheridan PPA.pdf",
            "GLD.PPA.Canton.pdf",
            "Skyway PPA.pdf",
            "PP Agreement - Emerald Garden - Mt Kemble.pdf",
            "PP Agreement - RSP - Mt Hope.pdf",
        ]
    )

    file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "Sheridan PPA.pdf",
            "GLD.PPA.Canton.pdf",
            "Skyway PPA.pdf",
            "PP Agreement - Emerald Garden - Mt Kemble.pdf",
            "PP Agreement - RSP - Mt Hope.pdf",
            "PP Agreement - Shine - DuQuoin.pdf",
            "Sunraise.PPA.Enterprise.pdf",
        ]
    )

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        return self.get_terms_and_instructions()


@dataclasses.dataclass
class OMPipelineConfig(PipelineConfig):
    """Configuration for the operation and maintenance agreement term_extraction."""

    pipeline_name: str = "om"
    project_previews_folder: str = (
        "project-previews-enriched-not-provided-false-positives"
    )
    chunk_size: int = 6000
    k: int = 5
    model_type: str = "CLAUDE"
    few_shot_file_names: List[str] = dataclasses.field(default_factory=lambda: [])
    short_terms_few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "O&M Agreement - Emerald Green - Cape Fear.pdf",
            "O&M- Bullrock - Lakeville.pdf",
            "Enterprise O&M.pdf",
            "O&M - Emerald Garden - Mt Kimble.pdf",
            "O&M Agreement - GLD- Canton.pdf",
        ]
    )

    file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "O&M Agreement - Emerald Green - Cape Fear.pdf",
            "O&M- Bullrock - Lakeville.pdf",
            "Enterprise O&M.pdf",
            "O&M - Emerald Garden - Mt Kimble.pdf",
            "O&M Agreement - GLD- Canton.pdf",
            "O&M Agreement - Novel - Bartel.pdf",
            "O&M Agreement - RSP - Mt Hope.pdf",
            "O&M Agreement - Shine - DuQuoin.pdf",
            "O&M Agreement - SunRaise - Pequawket Trail Baldwin.pdf",
        ]
    )

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        return self.get_terms_and_instructions()


@dataclasses.dataclass
class EPCPipelineConfig(PipelineConfig):
    """Configuration for the engineering,
    procurement and construction agreement term_extraction."""

    pipeline_name: str = "epc"
    project_previews_folder: str = "project-previews"
    chunk_size: int = 6000
    k: int = 5
    model_type: str = "CLAUDE"
    few_shot_file_names: List[str] = dataclasses.field(default_factory=lambda: [])
    short_terms_few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "EPC Agreement - Novel - Bartel.pdf",
            "EPC Agreement - SunRaise - Pequawket Trail Baldwin.pdf",
            "210331 233 Randolph 74 Solar I EPC Agreement executed.pdf",
            "EPC - Blue Sky - Felicita Town Center.pdf",
            "EPC - Emerald Garden - Mt Kimble.pdf",
            "EPC Agreement - Bullrock - Lakeville.pdf",
        ]
    )

    file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "EPC Agreement - Novel - Bartel.pdf",
            "EPC Agreement - SunRaise - Pequawket Trail Baldwin.pdf",
            "210331 233 Randolph 74 Solar I EPC Agreement executed.pdf",
            "EPC - Blue Sky - Felicita Town Center.pdf",
            "EPC - Emerald Garden - Mt Kimble.pdf",
            "EPC Agreement - Bullrock - Lakeville.pdf",
            "EPC Agreement - GLD - Canton.pdf",
            "EPC Agreement - RSP - Mt Hope.pdf",
            "EPC Agreement - Shine - DuQuoin.pdf",
            "EPC Agreement - SunRaise - Enterprise.pdf",
        ]
    )

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        return self.get_terms_and_instructions()


@dataclasses.dataclass
class SubscriberMgmtPipelineConfig(PipelineConfig):
    """Configuration for the subscriber management agreement term_extraction."""

    pipeline_name: str = "subscriber-management-agreement"
    project_previews_folder: str = "project-previews"
    documents_folder: str = "documents_v2"
    chunk_size: int = 6000
    k: int = 5
    model_type: str = "CLAUDE"
    few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "Ampion-SunRaise MSA (Executed Version 12.15.20).pdf",
            "Bartel Subscriber Agreement.pdf",
            "Lakeville SunCentral Master Services Agreement FINAL 2020 0831.pdf",
        ]
    )
    short_terms_few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: []
    )

    file_names: Sequence[str] | Sequence[Sequence[str]] = dataclasses.field(
        default_factory=lambda: [
            [
                "Mt Hope Subscription Agreement.pdf",
                "Subscriber Management First Amendment - Clean.pdf",
            ],
            "PowerMarket Master Service Agreement - Canton.pdf",
            "Sheridan Road Solar Farm_ LLC - Subscriber Management "
            "Agreement (NES 9.3.21).pdf",
            "Skyway Avenue Solar Farm_ LLC - Subscriber Management "
            "Agreement (NES 9.24.21).pdf",
            [
                "Williams Acres Solar Subscription Agreement.pdf",
                "Subscriber Management First Amendment - Clean (1).pdf",
            ],
        ]
    )
    keys: List[str] = dataclasses.field(default_factory=lambda: [])

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        terms_and_definitions = get_terms_and_instructions(
            self.get_terms_instructions_path()
        )
        if self.keys:
            terms_and_definitions = terms_and_definitions[
                terms_and_definitions["Key Items"].isin(self.keys)
            ]
        return terms_and_definitions


@dataclasses.dataclass
class OMProductionGuarantee(PipelineConfig):
    """Configuration for the operation
    and maintenance production guarantee term_extraction."""

    pipeline_name: str = "om-production-guarantee"
    project_previews_folder: str = "project-previews"
    chunk_size: int = 6000
    k: int = 5
    model_type: str = "CLAUDE"
    few_shot_file_names: List[str] = dataclasses.field(default_factory=lambda: [])
    short_terms_few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: []
    )

    file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "Production Guarantee Example.pdf",
        ]
    )

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        return self.get_terms_and_instructions()


@dataclasses.dataclass
class LoanAgreementPipelineConfig(PipelineConfig):
    """Configuration for the Security / Loan Agreement term_extraction."""

    pipeline_name: str = "loan-agreement"
    project_previews_folder: str = "project-previews"
    chunk_size: int = 6000
    k: int = 5
    model_type: str = "CLAUDE"
    few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "1 - Construction Loan Agreement.pdf",
            "EXECUTED Construction Loan Documents - 233 Randolph 74 Solar I 090721.pdf",  # noqa
            "[EXECUTED] M1 Bank - REA-Canton Rd - Construction Loan Documents - EXECUTION VERSION_opt.pdf",  # noqa
        ]
    )
    short_terms_few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: []
    )

    file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "1136420v1-Lakeville - GPS Loan - Loan Agreement - FINAL_Executed Copy.pdf",  # noqa
            "[EXECUTED] Construction Loan Documents - Mt Hope Solar (00028700-2xEECD3).pdf",  # noqa
            "DuQuoin Solar Executed FMW Loan Docs.pdf",
            "loan-240471-Loan and Security Agreement (Construction).pdf",
            "Novel Bartel Solar Executed Loan Docs.pdf",
            "Pequawket - 1 - Construction Loan Agreement + Pequawket.Crestmark.LoanExtension.pdf",  # noqa
        ]
    )

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        return self.get_terms_and_instructions()


@dataclasses.dataclass
class PVSystPipelineConfig(PipelineConfig):
    """Configuration for the PVsyst term_extraction."""

    pipeline_name: str = "pv-syst"
    project_previews_folder: str = "project-previews"
    chunk_size: int = 6000
    k: int = 5
    add_tables: bool = True
    model_type: str = "CLAUDE"
    processor_id: str = DOC_AI_PROCESSOR["TABLE_EXTRACTOR"]
    use_gcs_storage = True

    few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "2019-10-30 Bartel_PVSyst.pdf",
            "DuQuoin.PVSYST REV. 12-17-2019.pdf",
            "Mt Hope PVSYS.pdf",
        ]
    )
    short_terms_few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "2019-10-30 Bartel_PVSyst.pdf",
            "DuQuoin.PVSYST REV. 12-17-2019.pdf",
            "Mt Hope PVSYS.pdf",
        ]
    )

    file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "08-17-21_Novel Denzer -IFC_PVSyst_1426kWdc_metoenorm.pdf",
            "Asbuilt PVSyst_Pequawket Trl Balwdin_061621.pdf",
            "Benedix - PVSYST.pdf",
            "BP Felecita Town Center - PVSyst Package.pdf",
            "Canton GLC Solar PVSyst_ IFC Update_ with full clearing_ LW Seddon_ 22-Jul-2022.pdf",  # noqa
            "Dunn PVSYS.pdf",
            "Hayfield I.PVSyst - PVWatts - Helios-600.pdf",
            "Isanti IFC PVSYST.pdf",
            "Lakeville Final Enertis PVsyst 2020 1125.pdf",
            "NC_Cape Fear_PVsyst_07192021.pdf",
            "PVSyst As-Built_Enterprise Ave Gardiner_01-25-2021.pdf",
            "St. Louis.PVSyst.pdf",
        ]
    )

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        return self.get_terms_and_instructions()


@dataclasses.dataclass
class Phase1ESAConfig(PipelineConfig):
    """Configuration for the Phase 1 ESA term_extraction.

    "Environmental Site Assessment. Section 11.6 of HoldCo Operating
    Agreement has Environmental Protection.
    Sponsor indemnifies and holds harmless Investor member and its
    partners against and from any and all
    claims under or on account of any environmental laws

    Find out if there are environmental issues that effect the
    program (governmental regulation).
    federal requirement. determine if there are requirements.
    if there are, evaluate further...
    differentiate from renewable energy credit.
    this is a recognized environmental condition**"
    """

    pipeline_name: str = "phase-1-esa"
    project_previews_folder: str = "project-previews"
    chunk_size: int = 6000
    k: int = 5
    model_type: str = "CLAUDE"
    few_shot: bool = True
    few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "T121333_HEP-PE_RPT_Randolph_PhaseIESA_2021.07.19.pdf",
            "DuQuoin Solar_ LLC - DuQuoin Waste Water Treatment Plant Proposed Array - Phase I ESA.pdf",  # noqa
            "Mt Hope Phase 1 Env Site Assessment.pdf",
        ]
    )
    short_terms_few_shot_file_names: List[str] = dataclasses.field(
        default_factory=lambda: []
    )

    file_names: List[str] = dataclasses.field(
        default_factory=lambda: [
            "19447 Baldwin ESA 2022-01-19.pdf",
            "Phase I ESA - Augusta Road Bowdoin Solar LLC.pdf",
            "Larsen PHASE I - Lakeville Road Geneseo- Reliance update 11-30-20.pdf",
            "2023.05.25 Nutting Ridge Solar Phase I ESA.pdf",
            "Updated Phase I Mt Kemble 070921.pdf",
            "FINAL_REA_Canton, ME_Phase I ESA_20231115 (1).pdf",
            "2019.12.11_Bartel_Phase I ESA.pdf",
        ]
    )

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        return self.get_terms_and_instructions()


@dataclasses.dataclass
class OperatingAgreementPipelineConfig(PipelineConfig):
    """Configuration for the Operating Agreement term_extraction."""

    pipeline_name: str = "operating-agreement"
    project_previews_folder: str = "project-previews"
    chunk_size: int = 6000
    overlap_factor: int = 2
    k: int = 5
    model_type: str = "CLAUDE"
    folder_structure: bool = True
    use_gcs_storage: bool = True

    few_shot_file_names: Sequence[str] = dataclasses.field(
        default_factory=lambda: [
            "Blue Sky Utility Portfolio II 2020 AR OpA 2020.12.28.pdf",
            "Lakeville Holdco AR OpA (1).pdf",
            "Cape Fear - Hills Energy Holding_ LLC - Amended and Restated Operating Agreement [Executed].pdf",  # noqa
        ]
    )
    short_terms_few_shot_file_names: Sequence[str | Sequence[str]] = dataclasses.field(
        default_factory=lambda: []
    )

    file_names: Sequence[str | Sequence[str]] = dataclasses.field(
        default_factory=lambda: [
            "Enterprise Solar Holdings OpA.pdf",
            "executed Foss _ REA MN Holdco agreement.pdf",
            "IL Foss.Holdco LLC Agreement.exec (002).pdf",
            "Mt Kemble.Holdco Agreement.Execution.pdf",
            [
                "OR Foss 2019 Solar Holdings.pdf",
                "1st Amendment to OA for OR Foss 2019 Solar Holdings_executed.pdf",
            ],
            "AZ-REA 2021 ME.holdco agreement.FINAL EXECUTED.pdf",
        ]
    )

    def get_terms_and_definitions(self) -> pd.DataFrame:
        """Load the terms and definitions from the csv file."""
        return self.get_terms_and_instructions()
