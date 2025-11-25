# flake8: noqa
import textwrap
from typing import Any, List, Optional

from langchain.prompts import PromptTemplate
from langchain_core.prompts import FewShotPromptTemplate

from src.pipelines.constants import NO_POISON_PILLS_STR, NOT_PROVIDED_STR


def term_summary_prompt_template() -> str:
    """Create a prompt template for the term summary."""
    # CLAUDE
    template = (
        "{instructions}"
        + """
<actual_case>
Text:
```
{legal_terms}...
```
Data retrieved:
"""
    )
    return template


def rag_prompt_template() -> Any:
    """Create a prompt template for the rag pipeline."""
    rag_prompt_template_base = textwrap.dedent(
        """
                    1. Read the provided document carefully, paying attention to the specific sections and parts of sections that contain statements regarding the term.
                    
                    2. Identify the sections or parts of sections that contain the term, as defined in the definition.
                    
                    3. Copy the exact text of the relevant sections or parts of sections that contain the term.
                    
                    4. Ensure that the copied text is accurate and complete, and that it does not contain any additional information or context.
                    
                    5. Double-check the copied text to ensure that it meets the requirements of the instructions and that it is in the correct format.
                    
                    6. If there is no relevant information in the document, print the exact string text "{not_provided_str}"
                    
                    USE INSTRUCTIONS MENTIONED BELOW TO EXTRACT NEEDED TEXT. DO EVERYTHING ACCORDING TO INSTRUCTIONS:
                    BE AS PRECISE AS POSSIBLE, TRY TO ANSWER THE USERS REQUEST WITH THE BEST ABILITY THAT YOU CAN. 
                    
                    {input}
                    <document>
                    {context}
                    </document>
                    Your answer should be based solely on text of document no other sources are allowed.
                    Your output should contain only direct citations from the document.
                    Make 100% sure that the text you provide is accurate and complete and contains in the document.
                    If there is no relevant information in the document, print the exact string text "{not_provided_str}".
                    The direct citation from document text of section containing the term:
                """
    )
    return PromptTemplate.from_template(rag_prompt_template_base).partial(
        not_provided_str=NOT_PROVIDED_STR
    )


def rag_prompt_template_pvsyst() -> Any:
    """Create a prompt template for the rag pipeline."""
    rag_prompt_template_base = textwrap.dedent(
        """
                    1. Read the provided document carefully, paying attention to the specific sections and parts of sections that contain statements regarding the value.

                    2. Identify the sections or parts of sections that contain the value, as defined in the definition.

                    3. Ensure that the found value is accurate and complete, and that it does not contain any additional information or context.

                    4. Double-check the copied value to ensure that it meets the requirements of the instructions and that it is in the correct format.

                    5. If there is no relevant information in the document, print the exact string text "{not_provided_str}"

                    USE INSTRUCTIONS MENTIONED BELOW TO EXTRACT NEEDED VALUE. DO EVERYTHING ACCORDING TO INSTRUCTIONS:
                    BE AS PRECISE AS POSSIBLE, TRY TO ANSWER THE USERS REQUEST WITH THE BEST ABILITY THAT YOU CAN. 

                    {input}
                    <document>
                    {context}
                    </document>
                    Your answer should be based solely on text of document no other sources are allowed.
                    Make 100% sure that the vlue you provide is accurate and complete and contains in the document.
                    If there is no relevant information in the document, print the exact string text "{not_provided_str}".
                    The exact precise value:
                """
    )
    return PromptTemplate.from_template(rag_prompt_template_base).partial(
        not_provided_str=NOT_PROVIDED_STR
    )


def rag_prompt_template_pvsyst_units() -> Any:
    """Create a prompt template for the rag pipeline."""
    rag_prompt_template_base = textwrap.dedent(
        """1. Use the value provided and retrieve the correct units from text to output.
        2. OUTPUT ONLY THE VALUE WITH CORRECT UNITS.
        
THE VALUES: {value}
EXPECTED UNITS FORMAT: [Wp, kWac, MWh/year, kWh/kWp/year, MWh, kWh/m²]
THE TEXT: {text}
THE VALUE WITH CORRECT UNITS:"""
    )
    return PromptTemplate.from_template(rag_prompt_template_base)


def retrieve_full_text_of_sections() -> Any:
    """Create a prompt template for the rag pipeline."""
    rag_prompt_template_base = textwrap.dedent(
        """## Retrieve full text of sections: {input}
        <document>
        {context}
        </document>
        FULL TEXT OF SECTIONS {input}:"""
    )
    return PromptTemplate.from_template(rag_prompt_template_base)


def structure_text_of_sections() -> Any:
    """Create a prompt template for the rag pipeline."""
    rag_prompt_template_base = textwrap.dedent(
        """## Delete duplicated text of sections and keep only text of sections: {input}
         <text>
        {input}
        </text>
        TEXT OF SECTIONS :"""
    )
    return PromptTemplate.from_template(rag_prompt_template_base)


def prompt_check_for_references() -> Any:
    """Create a prompt template for the rag pipeline."""
    rag_prompt_template_base = textwrap.dedent(
        """<system_prompt>
YOU ARE A TEXT-PARSING SPECIALIST EXPERTLY TRAINED IN EXTRACTING SPECIFIC INFORMATION FROM TEXTUAL DATA. YOUR TASK IS TO IDENTIFY AND RETRIEVE ONLY THE SECTION NUMBERS **MENTIONED EXPLICITLY** IN THE PROVIDED TEXT, WHILE STRICTLY FOLLOWING THE GUIDELINES BELOW:

### INSTRUCTIONS ###
1. **EXTRACT** ONLY the section numbers that are explicitly stated in the text. For example, if the text mentions "Section 3.1" or "Section IV," you should only retrieve "3.1" and "IV."
2. **DO NOT** include any other section numbers that are not directly mentioned within the `<text>` tags.
3. **IGNORE** section numbers that are not clearly identified or are inferred (e.g., references to "above section" or "following section").
4. **PRESENT** your answer as a single, comma-separated list in the format: `SECTION NUMBERS MENTIONED IN THE TEXT: [list of section numbers]`.

### INPUT ###
```
<text>
{text}
</text>
```

### DESIRED OUTPUT FORMAT ###
```
SECTION NUMBERS MENTIONED IN THE TEXT: [list of section numbers]
```

### WHAT NOT TO DO ###
- **DO NOT** include any inferred or ambiguous section numbers not explicitly stated in the text.
- **DO NOT** retrieve numbers that are not in section format (e.g., ignore page numbers or item numbers).
- **DO NOT** include any additional formatting or text outside of the requested list format.

</system_prompt>"""
    )
    return PromptTemplate.from_template(rag_prompt_template_base)


def prompt_template_instructions(
    term: str,
    instructions: str,
) -> str:
    """Create a prompt template for the pipeline."""

    prompt_template_base = PromptTemplate.from_template(
        "Term to look for: {term}\n" "{instructions}\n"
    )
    return prompt_template_base.format(term=term, instructions=instructions)


def prompt_template(
    term: str, definition: str, examples: Optional[List[str]] = None
) -> str:
    """Create a prompt template for the pipeline."""

    if not examples:
        prompt_template_base = PromptTemplate.from_template(
            "Term to look for: {term}\n" "Definition of term: {definition}\n"
        )
        return prompt_template_base.format(term=term, definition=definition)

    prompt_template_base = PromptTemplate.from_template(
        "Term to look for: {term}\n"
        "Definition of term: {definition}\n"
        "Examples of answers:\n"
        "{few_shots_prompt}"
    )

    examples_dicts = [
        {"example": example[:200]}
        for example in examples
        if example != NOT_PROVIDED_STR
    ]

    example_prompt = PromptTemplate(
        input_variables=["example"], template="```\n{example}\n```"
    )
    few_shots_prompt = FewShotPromptTemplate(
        examples=examples_dicts,
        example_prompt=example_prompt,
        suffix="",
        example_separator="\n",
        input_variables=[],
    )

    return prompt_template_base.format(
        term=term, definition=definition, few_shots_prompt=few_shots_prompt.format()
    )


def poison_pills_prompt_template(legal_term: str, short_term: str, rule: str) -> str:
    prompt = textwrap.dedent(
        """
        YOU ARE A SENIOR DUE DILIGENCE MANAGER AT A LEADING SOLAR ENERGY COMPANY, TASKED WITH THE CRITICAL RESPONSIBILITY OF VERIFYING THE ACCURACY AND COMPLIANCE OF TEXT CITATIONS WITHIN DOCUMENTS RELATED TO SOLAR ENERGY PROJECTS. YOUR EXPERTISE IN LEGAL AND REGULATORY COMPLIANCE IS ESSENTIAL TO ENSURE THAT ALL CONTRACTS AND AGREEMENTS REFLECT THE CORRECT LEGAL STANDARDS AND COMPANY POLICIES.
        
        **Task Description:**
        - REVIEW the provided text containing citations from a document.
        - CHECK each citation against the specified rule: "{rule}."
        - PROVIDE expert feedback: If a citation violates the rule, detail the specific issue and suggest corrective actions. If all citations comply, return the phrase "{no_poison_pills_str}."
        
        **Chain of Thoughts:**
        1. **Understanding the Rule:**
           - Clearly comprehend the rule regarding leasing and property rights to apply it accurately during the review.
           - Note the key components of the rule which focus on ownership and leasing rights.
        
        2. **Reviewing the Text:**
           - Identify each citation in the text that pertains to leasing or property rights.
           - Analyze the context and content of these citations to see if they conform to the rule.
        
        3. **Evaluation and Feedback:**
           - For each citation that violates the rule, explain the discrepancy and provide detailed advice on how to address the issue.
           - If all citations are compliant, confirm this with the specified safe phrase.
        
        4. **Documentation and Reporting:**
           - Document your findings and recommendations clearly and concisely.
           - Prepare a summary report of the compliance check for internal use.
        
        **What Not To Do:**
        - DO NOT OVERLOOK ANY CITATION THAT REQUIRES REVIEW.
        - AVOID MISINTERPRETING THE RULE OR APPLYING IT INCORRECTLY.
        - NEVER LEAVE ERRORS UNADDRESSED IN THE FEEDBACK.
        - DO NOT FORGET TO PROVIDE CLEAR AND ACTIONABLE RECOMMENDATIONS FOR NON-COMPLIANT ISSUES.
        - DO NOT FAIL TO USE THE SPECIFIED PHRASE "{no_poison_pills_str}" WHEN ALL CITATIONS ARE COMPLIANT.
        
        Rule that needs to be checked for alignment with the legal terms:
        ```
        {rule}
        ```
        Short version of the term that needs to be checked for alignment with the rule:
        ```
        {short_term}
        ```
        Legal terms that need to be checked for alignment with the rule:
        ```
        {legal_term}
        ```
        ANSWER:"""
    )

    return PromptTemplate.from_template(prompt).format(
        no_poison_pills_str=NO_POISON_PILLS_STR,
        legal_term=legal_term,
        short_term=short_term,
        rule=rule,
    )


def poison_pill_presented_prompt_template(text: str) -> str:
    """
    Create a prompt that will answer yes or no if poison pills are presented in the text.
    """
    prompt = textwrap.dedent(
        f"""
        Read this text and summarise it as answer to a question. Poison pills are presented yes/no?
        Text:
        ```
        {text}
        ```
        Answer in json format: {{\"rules_violation\": \"yes/no\"}}    
        """
    )

    return prompt


def poison_pills_short_prompt_template(text: str) -> str:
    prompt = textwrap.dedent(
        f"""
        Rephrase this text with one sentence. Sentence should answer a question: If any rules violations are present and why?
        Text to rephrase:
        ```
        {text}
        ```
        Q: Any poison rules violations presented? Why?
        A:"""
    )

    return prompt


def poison_pills_bullet_points_prompt_template(text: str) -> str:
    prompt = textwrap.dedent(
        f"""
        YOU ARE A SENIOR COMPLIANCE ANALYST WITH EXPERTISE IN IDENTIFYING AND EXPLAINING RULE VIOLATIONS IN TEXTUAL DOCUMENTS. YOUR TASK IS TO REPHRASE THE PROVIDED TEXT INTO 3-5 CONCISE BULLET POINTS. THESE BULLET POINTS SHOULD CLEARLY EXPLAIN WHY THE TEXT IS CONSIDERED A VIOLATION OF THE RULES.

        **Instructions:**
        - REPHRASE the provided text into 3-5 clear and concise bullet points.
        - Each bullet point should EXPLAIN specifically why the text violates the rules.
        
        **Chain of Thoughts:**
        1. **Analyzing the Text:**
           - Carefully read the provided text to understand its content and context.
           - Identify specific parts of the text that violate the rules.
        
        2. **Rephrasing into Bullet Points:**
           - Summarize the key points of the violation.
           - Ensure each bullet point clearly articulates a distinct reason for the rule violation.
        
        3. **Ensuring Clarity and Precision:**
           - Use precise language to explain the violations.
           - Make sure the bullet points are easy to understand and directly related to the rule.
        
        **What Not To Do:**
        - DO NOT INCLUDE VAGUE OR UNSPECIFIC REASONS IN THE BULLET POINTS.
        - AVOID REPHRASING WITHOUT CLEARLY LINKING TO THE RULE VIOLATIONS.
        - DO NOT EXCEED THE LIMIT OF 3-5 BULLET POINTS.
        
        **Text to rephrase:**
        {text}
        **Bullet points explaining why the text is a violation of the rules:**"""
    )

    return prompt


if __name__ == "__main__":
    input_prompt = prompt_template("term", "definition", ["example1", "example2"])
    print(input_prompt)
    print("=========================================")
    print(rag_prompt_template().format(input=input_prompt, context="context"))
