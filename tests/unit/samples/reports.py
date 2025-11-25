PBI_EMBED_TOKEN = "PowerBI.Embed.Token"
PBI_CACHE_VALUE = "Token.from.Cache"
POWER_BI_ACCESS_TOKEN_RESPONSE = {
    "token_type": "Bearer",
    "expires_in": 3599,
    "ext_expires_in": 3599,
    "access_token": "access.token.secret",
}
POWER_BI_REPORTS_RESPONSE = {
    "value": [
        {
            "id": "rep1",
            "name": "Report 1",
            "webUrl": "https://report-1.web.link",
            "embedUrl": "https://report-1.embed.url",
        },
        {
            "id": "rep2",
            "name": "Report 2",
            "webUrl": "https://report-2.web.link",
            "embedUrl": "https://report-2.embed.url",
        },
    ]
}
POWER_BI_EMBED_TOKEN_RESPONSE = {
    "token": PBI_EMBED_TOKEN,
}
POWER_BI_GENERIC_RESPONSE = {
    "@odata.context": "https://analysis.windows.net/v1.0/myorg/groups/59754a20-b37171f8ff51/$metadata#exports/$entity",
    "id": "MS9CbG9iSWRWMi1jNjZmOWFjOS0Q1I1ZkFjOXBjNFE2NksweDA4RWo5ZURIRDlIQ2dFMDFRPS4=",
    "createdDateTime": "2025-03-27T12:46:30.6114842Z",
    "lastActionDateTime": "2025-03-27T12:46:30.6114842Z",
    "reportId": "8211a945-e2b2037178d5",
    "status": "NotStarted",
    "percentComplete": 0,
    "expirationTime": "0001-01-01T00:00:00Z",
}

EXPECTED_REPORTS_RESPONSE = {
    "items": [
        {
            "id": "rep1",
            "name": "Report 1",
            "web_url": "https://report-1.web.link",
            "embed_url": "https://report-1.embed.url",
        },
        {
            "id": "rep2",
            "name": "Report 2",
            "web_url": "https://report-2.web.link",
            "embed_url": "https://report-2.embed.url",
        },
    ]
}

EXPECTED_EMBED_TOKEN_RESPONSE = {"embed_token": PBI_EMBED_TOKEN}
EXPECTED_EMBED_TOKEN_RESPONSE_FROM_CACHE = {"embed_token": PBI_CACHE_VALUE}

PBI_EXPORT_REQUEST_BODY = {
    "format": "PDF",
    "pages": [{"pageName": "ReportSection5678efgh"}],
    "reportLevelFilters": [
        {
            "filter": "DimCompany/CompanyId eq 1",
            "filterType": 0,
            "target": {"table": "DimCompany", "column": "CompanyId"},
        }
    ],
}
