import logging
from typing import Any, Dict, List

import numpy as np
from langchain_core.prompts import PromptTemplate

from src.deployment.fast_api.models.input import CoterminousInputItem
from src.deployment.fast_api.models.output import (
    ComparisonStatus,
    CoterminousOutputItem,
)
from src.gen_ai.gen_ai import get_llm
from src.pipelines.co_terminus_check.prompts import co_terminus_prompt


logger = logging.getLogger(__name__)


class CoTerminusCheck:
    def __init__(self) -> None:
        prompt = PromptTemplate(
            template=co_terminus_prompt,
            input_variables=[
                "document_type_1",
                "document_type_2",
                "key_item_1",
                "key_item_2",
                "value_1",
                "value_2",
            ],
        )

        self.co_terminus_chain = prompt | get_llm(model_type="CLAUDE")

    def run_batch_validate(
        self, key_items_to_compare: List[CoterminousInputItem]
    ) -> List[CoterminousOutputItem]:
        """
        Validate the key items.
        :param key_items_to_compare:
        :return:
        """
        logger.info(f"STARTING EVALUATION: {key_items_to_compare}")
        assert key_items_to_compare, "No key items to compare"
        assert all(
            len(item.sources) >= 2 for item in key_items_to_compare
        ), "Each key item must have at least 2 sources"
        comparison_pairs = self.generate_comparison_pairs(key_items_to_compare)
        results = self.co_terminus_chain.batch(comparison_pairs)
        results = self.__check_response([result.content for result in results])
        results = [
            {"result": result, "name": key_item["name"]}
            for result, key_item in zip(results, comparison_pairs)
        ]
        grouped_results = self.group_responses(results)
        results = self.map_to_output(grouped_results)
        logger.info(f"GENERATED EVALUATION: {results}")
        return results  # type: ignore

    @staticmethod
    def generate_comparison_pairs(
        items: List[CoterminousInputItem],
    ) -> List[Dict[str, str | int | float]]:
        """
        Generate comparison pairs.
        :param items:
        :return:
        """
        return [
            {
                "name": i.name,
                "document_type_1": i.sources[0].document_name,
                "key_item_1": i.sources[0].key_item,
                "value_1": i.sources[0].value,
                "document_type_2": source.document_name,
                "key_item_2": source.key_item,
                "value_2": source.value,
            }
            for i in items
            for source in i.sources[1:]
        ]

    @staticmethod
    def map_to_output(results: Dict[str, bool]) -> List[CoterminousOutputItem]:
        """
        Map the results to the output.
        :param results:
        :return:
        """
        return [
            CoterminousOutputItem(status=ComparisonStatus.from_bool(result), name=key)
            for key, result in results.items()
        ]

    @staticmethod
    def group_responses(results: List[Dict[str, Any]]) -> Dict[str, bool]:
        """
        Group the responses.
        :param results:
        :return:
        """
        grouped_results: dict[Any, Any] = {}
        for result in results:
            name = result["name"]
            if name not in grouped_results:
                grouped_results[name] = []
            grouped_results[name].append(result["result"])

        # Evaluate if all results for each 'name' are True
        evaluated_results: Dict[str, bool] = {
            name: all(res_list) for name, res_list in grouped_results.items()
        }
        return evaluated_results

    @staticmethod
    def __check_response(results: List[Any]) -> List[Any]:
        """
        Validate the responses.
        :param results: List of TRUE/FALSE responses from the AI Model evaluation.
        :return:
        """
        mapping = {"true": True, "false": False}
        for i, result in enumerate(results):
            try:
                results[i] = mapping[CoTerminusCheck.parse_result(result)]
            except KeyError:
                results[i] = np.nan
        return results

    @staticmethod
    def parse_result(result: str) -> str:
        return (
            result.strip()
            .split("<answer>")[-1]
            .replace("</answer>", "")
            .strip()
            .lower()
        )
