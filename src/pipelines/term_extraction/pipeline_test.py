from src.pipelines.term_extraction.pipeline import Pipeline
from src.pipelines.term_extraction.pipeline_config import (
    InterconnectionAgreementPipelineConfig,
)


if __name__ == "__main__":
    pipeline_config = InterconnectionAgreementPipelineConfig()
    pipeline = Pipeline.from_config(pipeline_config)
    chain = pipeline._build_a_chain(
        ["/Users/odeine/PycharmProjects/ilios-DocAI/data/table1.pdf"]
    )

    while True:
        user_input = input()
        if user_input.lower() == "exit":
            break
        print(chain.invoke({"input": user_input})["answer"])
