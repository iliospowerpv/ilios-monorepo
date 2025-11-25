import json

from matplotlib.font_manager import json_dump


data = {
    "id": 42,
    "items": [
        {
            "name": "Initial Term",
            "sources": [
                {
                    "document_name": "Site Lease",
                    "key_item": "Initial Term",
                    "value": "Yes",
                },
                {
                    "document_name": "PPA and Amendments",
                    "key_item": "Term",
                    "value": "By the previous agreement",
                },
            ],
        },
        {
            "name": "Mechanical Completion Date",
            "sources": [
                {
                    "document_name": "Interconnection Agreement and Amendments",
                    "key_item": "Mechanical Completion Date",
                    "value": "11.22.63",
                },
                {
                    "document_name": "EPC Agreement",
                    "key_item": "Mechanical Completion Date",
                    "value": "Nov 11, 1963",
                },
            ],
        },
        {
            "name": "Nameplate Capacity (System Size)",
            "sources": [
                {
                    "document_name": "Interconnection Agreement and Amendments",
                    "key_item": "Nameplate Capacity (System Size)",
                    "value": 15,
                },
                {
                    "document_name": "PPA and Amendments",
                    "key_item": "Nameplate Capacity",
                    "value": 15.00,
                },
                {
                    "document_name": "EPC Agreement",
                    "key_item": "System Size",
                    "value": 15,
                },
                {
                    "document_name": "O&M Agreement",
                    "key_item": "Nameplate Capacity",
                    "value": "15",
                },
            ],
        },
        {
            "name": "PPA Net Energy Rate",
            "sources": [
                {
                    "document_name": "O&M Agreement",
                    "key_item": "PPA Net Energy Rate",
                    "value": "Green",
                },
                {
                    "document_name": "PPA and Amendments",
                    "key_item": "Power Purchase Agreement Rate",
                    "value": "AAA+",
                },
            ],
        },
    ],
}

json_data = json.dumps(data, indent=4)
json_dump(data, "data.json")  # type: ignore
print(json_data)
