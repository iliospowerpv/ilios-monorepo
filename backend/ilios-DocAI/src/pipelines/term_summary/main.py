import click
from langchain.globals import set_debug

from src.pipelines.mappings import agreement_types
from src.pipelines.term_summary.pipeline_runner import ShortTermsPipelineRunner


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("agreement_type", type=str)
@click.option("-d", "--debug", is_flag=True, help="Enable debug mode")
def main(agreement_type: str, debug: bool) -> None:
    """Main function to run the term extraction pipeline.
    Args:
        agreement_type (str): The type of agreement to extract terms from.
        debug (bool): Whether to enable debug mode.
    Examples of usage:
        python3 -m src.pipelines.term_summary.main site-lease --debug
    """
    # Set debug mode based on the argument
    set_debug(debug)
    # Get the agreement type from the arguments
    agreement_type = agreement_type.lower()
    # Check if the provided agreement type is valid
    if agreement_type not in agreement_types:
        raise ValueError(
            f"Invalid agreement type. Expected one of {list(agreement_types.keys())}"
        )
    # Get the corresponding pipeline config class
    PipelineConfigClass = agreement_types[agreement_type]
    # Create the pipeline config
    pipeline_config = PipelineConfigClass()
    # Run the pipeline
    pipeline_runner = ShortTermsPipelineRunner(pipeline_config)
    pipeline_runner.run()


if __name__ == "__main__":
    main()
