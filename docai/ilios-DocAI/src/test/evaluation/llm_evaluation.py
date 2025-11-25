# flake8: noqa

import pytest

from src.validation.validation import get_evaluation_llm_chain, llm_evaluation


@pytest.mark.parametrize(
    "reference_answer, new_answer, expected",
    [
        ("Not provided.", "Not provided.", 2.0),
        ("Not provided.", "Not provided", 2.0),
        (
            "Not provided.",
            'The document does not appear to contain the term "Mechanical Completion Date" or any direct references to that specific term. There are no relevant quotes or sections that mention mechanical completion.',
            2.0,
        ),
        (
            "Not provided.",
            'The term "Degradation Amount" is not explicitly mentioned in the given document. There are no direct citations related to this term.',
            2.0,
        ),
        (
            "Not provided.",
            'The document does not appear to contain the term "Site Lease Prepayment (Y/N)". There are no direct citations relevant to this term. So the answer is: \n Not provided.',
            2.0,
        ),
        (
            "Not provided.",
            """The term "Site Lease Prepayment (Amount)" is not explicitly mentioned in the given document. However, there is a relevant section that discusses a payment related to the lease:

                          "Section 1.04. Lease Fee. In addition to the mutual agreements, covenants, and other consideration set forth in the Lease, Developer shall pay a construction commencement fee in the amount of $950,000.00 upon the commencement of construction of the System payable to Evergreen Energy, LLC and an annual rent to Owner in the amount of $135,000.00 per year (or $125,000.00 per year in the event the System only qualifies for 10 years of SRECS) ("Lease Fee") during the Operational Term (as defined herein).""",
            0,
        ),
        (
            "Not provided.",
            """The relevant section containing information about a Site Lease Prepayment is:

Section 1.04. Lease Fee. In addition to the mutual agreements, covenants, and other consideration set forth in the Lease, Developer shall pay a construction commencement fee in the amount of $950,000.00 upon the commencement of construction of the System payable to Evergreen Energy, LLC and an annual rent to Owner in the amount of $135,000.00 per year (or $125,000.00 per year in the event the System only qualifies for 10 years of SRECS) ("Lease Fee") during the Operational Term (as defined herein). The first Lease Fee shall be paid on the day that the System reaches Commercial Operation (the "Commercial Operation Date") and any additional Lease Fee shall be made on each anniversary thereof during the Term of this Lease.

This section mentions a "construction commencement fee in the amount of $950,000.00" that the Developer must pay upon commencement of construction, which can be considered a prepayment for the site lease.""",
            0,
        ),
        (
            "Not provided.",
            """The relevant section containing information about "Default by Customer" is Section 6.6, which states:

"6.6.1 With written notice to CG and any Interconnection Financing Party, SDG&E shall have the right to terminate this Agreement upon the occurrence of any of the following:
(a) The failure or refusal of CG to cure any default or breach of this Agreement or of any other obligations to SDG&E, in accordance with this Agreement, unless excused by reason of Uncontrollable Forces as defined in Section 6.7 hereof.
(b) CG's failure to complete installation of the Generating Facility within two (2) years of the date of this Agreement; provided, however, that SDG&E shall have the right to extend said period for completing installation if CG has used due diligence and the failure was not due to Uncontrollable Forces under Section 6.7 hereof.
""",
            0,
        ),
    ],
)
def test_llm_evaluation(reference_answer: str, new_answer: str, expected: int) -> None:
    llm_chain, llm_chain_na = get_evaluation_llm_chain()
    result = llm_evaluation(reference_answer, new_answer, llm_chain, llm_chain_na)
    assert result == expected
