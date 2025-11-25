import enum
import os
from typing import Any

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer, pipeline


# Set the environment variable to disable the warning
os.environ["TOKENIZERS_PARALLELISM"] = "false"


# ENUM of the different types of injections
class InjectionType(enum.Enum):
    CODE = "code"
    INJECTION = "injection"


class InjectionError(ValueError):

    def __init__(self, kind: InjectionType, *args: Any) -> None:
        self.kind = kind
        super().__init__(*args)


def get_injection_classifier_llm() -> Any:
    tokenizer = AutoTokenizer.from_pretrained(
        "ProtectAI/deberta-v3-base-prompt-injection-v2"
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        "ProtectAI/deberta-v3-base-prompt-injection-v2"
    )

    classifier = pipeline(
        "text-classification",
        model=model,
        tokenizer=tokenizer,
        truncation=True,
        max_length=512,
        device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
    )
    return classifier


def get_code_classifier_llm() -> Any:
    tokenizer = AutoTokenizer.from_pretrained(
        "philomath-1209/programming-language-identification"
    )
    model = AutoModelForSequenceClassification.from_pretrained(
        "philomath-1209/programming-language-identification"
    )

    classifier = pipeline(
        "text-classification",
        model=model,
        tokenizer=tokenizer,
        truncation=True,
        max_length=512,
        device=torch.device("cuda" if torch.cuda.is_available() else "cpu"),
    )
    return classifier


class InjectionClassifier:
    """
    Injection classifier class
    """

    def __init__(self) -> None:
        self.injection_classifier = get_injection_classifier_llm()
        self.code_classifier = get_code_classifier_llm()

    def check_for_injection(self, user_message: str) -> bool:
        res = self.injection_classifier(user_message)[0]
        if res["label"] == "INJECTION" and res["score"] > 0.9:
            raise InjectionError(
                InjectionType.INJECTION,
                f"Injection detected with probability {res['score']}",
            )

        res = self.code_classifier(user_message)[0]
        if res["score"] > 0.985:
            raise InjectionError(
                InjectionType.CODE, f"Code detected with probability {res['score']}"
            )

        return False
