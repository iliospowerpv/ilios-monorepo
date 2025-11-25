import logging
from typing import Any

import numpy as np
import pandas as pd

from src.gen_ai.gen_ai import get_llm
from src.pipelines.constants import NO_POISON_PILLS_STR, NOT_SUPPORTED_KEY_ITEM
from src.prompts.prompts import (
    poison_pill_presented_prompt_template,
    poison_pills_bullet_points_prompt_template,
    poison_pills_prompt_template,
    poison_pills_short_prompt_template,
)


logger = logging.getLogger(__name__)


class PoisonPillsPipeline:
    def __init__(self) -> None:
        """Initialize the PoisonPillsPipeline."""
        self.llm: Any = get_llm(model_type="GEMINI15")
        self.poison_pills_rules = pd.read_csv(
            "gs://doc_ai_storage/poison-pills/poison-pills-rules.csv"
        )

    def run(self, extracted_terms: pd.DataFrame) -> pd.DataFrame:
        """Run the PoisonPillsPipeline."""
        logger.info("Running the PoisonPillsPipeline")
        prompts = []
        key_items_rule = []
        for _, row in extracted_terms.iterrows():
            if (
                row["Legal Terms"]
                and not pd.isna(row["Legal Terms"])
                and (not (row["Legal Terms"] == NOT_SUPPORTED_KEY_ITEM))
            ):
                for _, rule in self.poison_pills_rules.iterrows():
                    logging.info(
                        f"Processing rule: {rule['Name']} key items: {row['Key Items']}"
                    )
                    if (row["Key Items"] in rule["Key Items"].split(";")) or (
                        rule["Key Items"] == "All"
                    ):
                        key_items_rule.append((row["Key Items"], rule["Name"]))
                        prompt = poison_pills_prompt_template(
                            legal_term=row["Legal Terms"],
                            short_term=row["Value"],
                            rule=rule["Prompt"],
                        )
                        prompts.append(prompt[::])

        poison_pills_comment = self.llm.batch(prompts)
        ans = pd.DataFrame(key_items_rule, columns=["Key Items", "Name"])
        if len(poison_pills_comment) == 0:
            ans["Poison Pills"] = "N/A"
            ans["Poison Pills Comment"] = "N/A"
            ans["Poison Pills Presented"] = "N/A"
            ans["Full Comments"] = "N/A"
            return ans
        ans["Poison Pills Comment"] = [
            comment.content for comment in poison_pills_comment
        ]
        ans["Poison Pills Presented"] = self.get_poison_pills_presented(
            ans["Poison Pills Comment"].tolist()
        )
        poison_pills_presented = ans.groupby("Key Items").apply(
            lambda x: "yes" if "yes" in x["Poison Pills Presented"].tolist() else "no"
        )
        ans_full = ans.groupby("Key Items").apply(
            lambda x: "\n".join(
                [
                    f"Rule name: {r['Name']}:\nComment:{r['Poison Pills Comment']}"
                    for _, r in x.iterrows()
                ]
            )
        )
        ans = ans.groupby("Key Items").apply(
            lambda x: "\n".join(
                [
                    f"Rule name: {r['Name']}:\nComment:{r['Poison Pills Comment']}"
                    for _, r in x.iterrows()
                    if r["Poison Pills Presented"] == "yes"
                ]
            )
        )
        ans = ans.reset_index().rename({0: "Poison Pills"}, axis=1)
        ans["Full Comments"] = ans_full.values

        ans["Poison Pills Presented"] = poison_pills_presented.values
        ans["Poison Pills Short Versions"] = self.get_poison_pills_short_version(
            ans["Poison Pills"].tolist()
        )
        ans["Poison Pills"] = self.get_poison_pills_bullet_points(
            ans["Poison Pills"].tolist(), ans["Poison Pills Presented"].tolist()
        )
        extracted_terms = extracted_terms.replace({pd.NA: "N/A"})
        extracted_terms = extracted_terms.merge(ans, on=["Key Items"], how="left")
        logger.info("Running the PoisonPillsPipeline completed successfully.")
        extracted_terms = extracted_terms.rename(
            {
                "Poison Pills": "Poison Pills Detailed",
                "Poison Pills Short Versions": "Poison Pills",
            },
            axis=1,
        )
        extracted_terms.to_csv("output_ppills_final.csv")
        poison_pills_columns = [
            "Key Items",
            "Value",
            "Legal Terms",
            "Poison Pills",
            "Poison Pills Presented",
            "Poison Pills Detailed",
        ]
        return extracted_terms[poison_pills_columns]

    def get_poison_pills_presented(self, poison_pills_comment: list[str]) -> list[str]:
        """Return a list of 'yes' or 'no' for each response
        based on the presence of NO_POISON_PILLS_STR."""
        # Create a list of tuples (index, response) for
        # responses that do not contain NO_POISON_PILLS_STR
        possibly_positive_poison_pill = [
            (i, resp)
            for i, resp in enumerate(poison_pills_comment)
            if NO_POISON_PILLS_STR.lower().strip() not in resp.lower().strip()
        ]

        # Extract the responses from the tuples
        possibly_positive_poison_pill_comment = [
            resp for i, resp in possibly_positive_poison_pill
        ]

        # Create prompts for responses that do not contain NO_POISON_PILLS_STR
        prompts = list(
            map(
                poison_pill_presented_prompt_template,
                possibly_positive_poison_pill_comment,
            )
        )

        # Execute batch for responses that do not contain NO_POISON_PILLS_STR
        poison_pills_presented_binary_json_response = self.llm.batch(prompts)
        poison_pills_presented_binary_json_response = [
            response.content for response in poison_pills_presented_binary_json_response
        ]

        # Initialize a list for the final results with the same length as responses
        poison_pills_presented_answer = ["no"] * len(poison_pills_comment)

        def parse_poison_pills_binary_json_response(json_response: str) -> Any:
            """Parse the poison pills binary_json_response."""
            try:
                if not json_response:
                    return "N/A"
                else:
                    return eval(
                        json_response.replace("```json", "").replace("```", "")
                    )["rules_violation"]
            except (KeyError, SyntaxError):
                logging.error(
                    "Error parsing pp binary_json_response: {}".format(json_response)
                )
                return "N/A"

        # Insert the batch results into their original positions
        for (i, _), binary_json_response in zip(
            possibly_positive_poison_pill, poison_pills_presented_binary_json_response
        ):
            poison_pills_presented_answer[i] = parse_poison_pills_binary_json_response(
                binary_json_response
            )[::]
        return poison_pills_presented_answer

    @staticmethod
    def get_poison_pills_short_version(responses: list[str]) -> Any:
        """Get poison pills short versions."""
        llm = get_llm(model_type="GEMINI15")
        prompts = list(map(poison_pills_short_prompt_template, responses))
        poison_pills_short_version = llm.batch(prompts)
        poison_pills_short_version = [
            response.content for response in poison_pills_short_version
        ]
        return list(poison_pills_short_version)

    def get_poison_pills_bullet_points(
        self, responses: list[str], pp_presented: list[str]
    ) -> list[Any]:
        """Get poison pills bullet points."""
        # Create a list of tuples (index, response) for not nan responses
        not_nan_responses = [
            (i, resp)
            for i, resp in enumerate(responses)
            if pd.notna(resp) and pp_presented[i] == "yes"
        ]
        # Extract the responses from the tuples
        not_nan_responses_values = [resp for i, resp in not_nan_responses]
        # Create prompts for not nan responses
        prompts = list(
            map(poison_pills_bullet_points_prompt_template, not_nan_responses_values)
        )
        # Execute batch for not nan responses
        pp_summaries_not_nan = self.llm.batch(prompts)
        pp_summaries_not_nan = [response.content for response in pp_summaries_not_nan]

        # Initialize a list for the final results with the same length as responses
        pp_summaries = [np.nan] * len(responses)

        # Insert the batch results into their original positions
        for (i, _), summary in zip(not_nan_responses, pp_summaries_not_nan):
            pp_summaries[i] = summary[::]
        return pp_summaries
