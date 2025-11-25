from pydantic import BaseModel, Field


class ReportListSchema(BaseModel):
    id: str = Field(examples=["0ba653a0"])
    name: str = Field(examples=["Yearly Investor's report"])
    webUrl: str = Field(  # noqa: N815
        examples=["https://app.powerbi.com/groups/59754a2071f8/reports/0ba653a0"],
        serialization_alias="web_url",
    )
    embedUrl: str = Field(  # noqa: N815
        examples=[
            "https://app.powerbi.com/reportEmbed?reportId=0ba653a0&groupId=59754a2071f8&w=2&config=eyJjbHVzd0LmFuYWx5c"
        ],
        serialization_alias="embed_url",
    )


class ReportsPaginator(BaseModel):

    items: list[ReportListSchema]


class ReportEmbedTokenSchema(BaseModel):
    embed_token: str = Field(examples=["6sLiie_lkth_udf17CK5e4FAAA=.eyJjbH2Vzc092ZXJQdWJsaWNJbnRlcm5ldCI6dHJ1ZX0="])
