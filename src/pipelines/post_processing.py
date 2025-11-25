import difflib
import re

import pandas as pd

from src.pipelines.constants import NOT_PROVIDED_STR


def project_preview_postprocessing(data: pd.DataFrame, full_text: str) -> pd.DataFrame:
    """
    Process the predicted terms and their summaries for a given agreement data.
    """
    data = data.rename(
        columns={"Predicted Legal Terms": "Legal Terms", "Term Summary": "Value"}
    )
    data.replace(NOT_PROVIDED_STR, "N/A", inplace=True)
    data.replace(" " + NOT_PROVIDED_STR, "N/A", inplace=True)
    data = assign_paragraphs(data, full_text)
    return data[["Key Items", "Value", "Legal Terms"]]


def find_hierarchy(term: str, full_text: str) -> str:
    """Find paragraph hierarchy in the text"""
    # Split the full text into paragraphs with identifiable markers
    paragraphs = re.split(r"\n(?=\d+\.)|\n(?=\([a-z]\))", full_text)

    # Preprocess term for matching
    term_first_line = term.strip().split("\n")[0]

    # Variables to hold the current numerical and letter part of the hierarchy
    current_num: str = ""
    current_letter: str = ""

    # Iterate over paragraphs to find where the term is located
    for i, para in enumerate(paragraphs):
        num_match = re.match(r"^(\d+)\.", para)
        letter_match = re.match(r"^\(([a-z])\)", para)

        if num_match:
            # Update current number and reset letter when a new number is encountered
            current_num = num_match.group(1)
            current_letter = ""  # Reset letter part since we're in a new section
        elif letter_match:
            # Update current letter
            current_letter = letter_match.group(1)

        # Check if the current paragraph contains the start of the term
        if term_first_line in para:
            # Construct the hierarchy string based on the current number and letter
            if current_letter:
                return f"{current_num}.({current_letter})"
            return current_num

    # Return a message if the term is not found in the hierarchy
    return ""


def get_overlap(s1: str, s2: str) -> str:
    """Get overlapping string between two strings"""
    s = difflib.SequenceMatcher(None, s1, s2)
    pos_a, pos_b, size = s.find_longest_match(0, len(s1), 0, len(s2))
    return s1[pos_a : pos_a + size]


def assign_paragraphs(
    predicted_legal_terms: pd.DataFrame, full_text: str
) -> pd.DataFrame:
    """Assign missing paragraph numbers for the predicted legal terms."""
    terms_with_paragraph_numbers = []
    para_nums = []
    for _, row in predicted_legal_terms.iterrows():
        if not row["Legal Terms"] or pd.isna(row["Legal Terms"]):
            terms_with_paragraph_numbers.append("")
            continue
        para_num = find_hierarchy(full_text, row["Legal Terms"])
        para_nums.append(para_num)
        if get_overlap(row["Legal Terms"][:10], para_num):
            overlap = get_overlap(row["Legal Terms"], para_num)
            terms_with_paragraph_numbers.append(
                row["Legal Terms"].replace(overlap, para_num)
            )
        else:
            terms_with_paragraph_numbers.append(para_num + row["Legal Terms"])
    predicted_legal_terms["Legal Terms"] = terms_with_paragraph_numbers
    return predicted_legal_terms
