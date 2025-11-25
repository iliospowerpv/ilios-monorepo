from langchain.prompts import PromptTemplate

full_template = """
"Act as a senior prompt engineer. Having this term, definition and examples of text to look for, you can start to look for the term in the text and understand the context."
Give me characteristics of the examples of text to look for, how to find this text in the document , what to look for , provide to me a set of rules
Term: {term}
Definition: {definition}

Examples of text:
{examples}"""
full_prompt = PromptTemplate.from_template(full_template)

for _, row in terms_and_definitions.iterrows():

    term = row["Key Items"]
    definition = row["Definitions"]

    examples = "\n\n".join(get_exaples(row["Key Items"]))

    inputs = {"term": term, "definition": definition, "examples": examples}
    chain = (full_prompt | llm)

    try:
        print(f"Term {term}")
        ans = chain.invoke(inputs)
        print("Prompt:")
        print(ans.content)

        print("Improved prompt:")
        print(improve_prompt(ans.content))

        print("-------------------------------------------------")

    except:
        pass