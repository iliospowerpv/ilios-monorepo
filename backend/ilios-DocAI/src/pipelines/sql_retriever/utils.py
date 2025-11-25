import difflib
from typing import List


def find_closest_match(word: str, word_list: List[str]) -> str | None:
    """Find the closest match to the given word in the word list."""
    closest_match = difflib.get_close_matches(word, word_list, n=1)
    return closest_match[0] if closest_match else None
