import copy

from app.models.file import FileParsingStatuses
from app.static.co_terminus_checks import CoTerminusComparisonStatuses
from app.static.default_site_documents_enum import SiteDocumentsEnum

# unit

# for the most used terms, create vars to represent names
RENEWAL_TERMS_KEY = "Renewal Terms"
MCD_KEY = "Mechanical Completion Date"

CO_TERM_FIXTURE_RESULTS = [
    {
        "name": "Initial Term",
        "sources": {"Site Lease": "Matching Value", "PPA - Power Purchase Agreement": "matching VALUE"},
        "status": "Equal",
    },
    {
        "name": RENEWAL_TERMS_KEY,
        "sources": {"Site Lease": "Value 1", "PPA - Power Purchase Agreement": "Value 2"},
        "status": "Pending",
    },
    {
        "name": MCD_KEY,
        "sources": {"Site Lease": "Yesterday", "PPA - Power Purchase Agreement": None},
        "status": "N/A",
    },
    {
        "name": "Nameplate Capacity (System Size)",
        "sources": {"Site Lease": "   ", "PPA - Power Purchase Agreement": None},
        "status": "N/A",
    },
]

CO_TERM_UPDATE_RESULT_API_ITEMS = [{"name": RENEWAL_TERMS_KEY, "status": CoTerminusComparisonStatuses.ambiguous.value}]

CO_TERM_RESULTS_EMPTY_RESPONSE = {"summary": [], "items": []}
CO_TERM_CONFIG = {
    "The Term": {
        "Site Lease": "Term",
        "PPA - Power Purchase Agreement": "The Term",
    }
}
CO_TERM_RESULTS_SAMPLE = [
    {
        "name": "The Term",
        "sources": {
            "Site Lease": "val1",
            "PPA - Power Purchase Agreement": "Val",
            # validates if agreement is not in config anymore it will not be returned
            "Deleted Agreement": "Something",
        },
        "status": "Equal",
    },
    {
        # illustrates the case if key not in config it will be skipped on the output
        "name": "Deleted Key",
        "sources": {"Site Lease": "val", "PPA - Power Purchase Agreement": "Val"},
        "status": "Equal",
    },
]
CO_TERM_RESULTS_API_RESPONSE = {
    "summary": [{"status": "Equal", "count": 1}],
    "items": [
        {
            "name": "The Term",
            "status": "Equal",
            "sources": {"Site Lease": "val1", "PPA - Power Purchase Agreement": "Val"},
        }
    ],
}

# integration

CO_TERM_CONFIG_MOCK = {
    # matched
    "Initial Term": {
        SiteDocumentsEnum.site_lease.value: "Initial Term",
        SiteDocumentsEnum.ppa_and_amendments.value: "Term",
    },
    # different
    RENEWAL_TERMS_KEY: {
        SiteDocumentsEnum.site_lease.value: RENEWAL_TERMS_KEY,
        SiteDocumentsEnum.ppa_and_amendments.value: RENEWAL_TERMS_KEY,
    },
    # one of is null
    MCD_KEY: {
        SiteDocumentsEnum.site_lease.value: MCD_KEY,
        SiteDocumentsEnum.ppa_and_amendments.value: MCD_KEY,
    },
    # all are nulls
    "Nameplate Capacity (System Size)": {
        SiteDocumentsEnum.site_lease.value: "Nameplate Capacity (System Size)",
        SiteDocumentsEnum.ppa_and_amendments.value: "Nameplate Capacity",
    },
}

CO_TERM_PARTIAL_RESULT = copy.deepcopy(CO_TERM_FIXTURE_RESULTS)
CO_TERM_PARTIAL_RESULT_RESPONSE = {"summary": [], "items": CO_TERM_PARTIAL_RESULT}
CO_TERM_BE_COMPLETED_RESULT = copy.deepcopy(CO_TERM_FIXTURE_RESULTS)
for item in CO_TERM_BE_COMPLETED_RESULT:
    if item["name"] == RENEWAL_TERMS_KEY:
        item["status"] = CoTerminusComparisonStatuses.equal.value
        item["sources"]["PPA - Power Purchase Agreement"] = "Value 1"
CO_TERM_BE_COMPLETED_RESULT_RESPONSE = {
    "summary": [
        {"status": CoTerminusComparisonStatuses.equal.value, "count": 2},
        {"status": CoTerminusComparisonStatuses.na.value, "count": 2},
    ],
    "items": CO_TERM_BE_COMPLETED_RESULT,
}


CO_TERM_UPDATE_RESULT_SUCCESS_PAYLOAD = {
    "status": FileParsingStatuses.completed.value,
    "items": [
        {"name": RENEWAL_TERMS_KEY, "status": CoTerminusComparisonStatuses.ambiguous.value},
        {"name": MCD_KEY, "status": CoTerminusComparisonStatuses.not_equal.value},
    ],
}

CO_TERM_COMPLETED_RESULT_SUCCESS = copy.deepcopy(CO_TERM_FIXTURE_RESULTS)
for item in CO_TERM_COMPLETED_RESULT_SUCCESS:
    if item["name"] == RENEWAL_TERMS_KEY:
        item["status"] = CoTerminusComparisonStatuses.ambiguous.value
    elif item["name"] == MCD_KEY:
        item["status"] = CoTerminusComparisonStatuses.not_equal.value
CO_TERM_COMPLETED_RESULT_SUCCESS_RESPONSE = {
    "summary": [
        {"status": CoTerminusComparisonStatuses.ambiguous.value, "count": 1},
        {"status": CoTerminusComparisonStatuses.equal.value, "count": 1},
        {"status": CoTerminusComparisonStatuses.na.value, "count": 1},
        {"status": CoTerminusComparisonStatuses.not_equal.value, "count": 1},
    ],
    "items": CO_TERM_COMPLETED_RESULT_SUCCESS,
}

CO_TERM_UPDATE_RESULT_ERROR_PAYLOAD = {"status": FileParsingStatuses.processing_failed.value, "items": []}

CO_TERM_COMPLETED_RESULT_ERROR = copy.deepcopy(CO_TERM_FIXTURE_RESULTS)
for item in CO_TERM_COMPLETED_RESULT_ERROR:
    if item["name"] == RENEWAL_TERMS_KEY:
        item["status"] = CoTerminusComparisonStatuses.error.value
CO_TERM_COMPLETED_RESULT_ERROR_RESPONSE = {"summary": [], "items": CO_TERM_COMPLETED_RESULT_ERROR}
