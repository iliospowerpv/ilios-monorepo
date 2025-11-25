import os

import pandas as pd

from src.settings import DATA_FOLDER


mapping = {
    "Site Lease": "site-lease",
    "PPA": "ppa",
    "EPC": "epc",
    "O&M": "om",
    "Interconnection Agreement": "interconnection-agreement",
    "Subscriber Management": "subscriber-management-agreement",
}

folders_mapping = {
    "site-lease": "project-previews-updated-enriched-and-not-provided-instr-fix",
    "ppa": "project-previews-false-positives-reviewed",
    "epc": "project-previews-updated",
    "om": "project-previews-enriched-not-provided-false-positives",
    "interconnection-agreement": "project-previews-updated-updated-pp-v2",
    "subscriber-management-agreement": "project-previews",
}


def main() -> None:
    # Read the project previews CSV file
    project_previews = pd.read_csv("project-previews.csv")
    # Initialize an empty DataFrame to store the merged data
    merged_data = pd.DataFrame()
    # Read the comparisons CSV file
    comparisons = pd.read_csv("comparisons.csv")

    # Loop over each row in the comparisons DataFrame
    for _, row in comparisons.iterrows():
        # Get the document names and key names
        document_name_1, key_name_1, _, document_name_2, key_name_2 = row

        # Loop over each row in the project previews DataFrame
        for _, project_row in project_previews.iterrows():
            # Get the file names for the two documents
            try:
                file_name_1 = project_row[mapping[document_name_1]]
                file_name_2 = project_row[mapping[document_name_2]]
            except KeyError:
                continue

            if pd.isnull(file_name_1) or pd.isnull(file_name_2):
                continue

            file_path_1 = os.path.join(
                DATA_FOLDER,
                mapping[document_name_1],
                folders_mapping[mapping[document_name_1]],
                file_name_1.replace(".pdf", ".csv"),
            )
            file_path_2 = os.path.join(
                DATA_FOLDER,
                mapping[document_name_2],
                folders_mapping[mapping[document_name_2]],
                file_name_2.replace(".pdf", ".csv"),
            )

            data_1 = pd.read_csv(file_path_1, index_col=0)
            data_2 = pd.read_csv(file_path_2, index_col=0)

            try:
                # Get the key items
                key_item_1 = data_1.loc[[key_name_1]][["Value", "Legal Terms"]]
                key_item_2 = data_2.loc[[key_name_2]][["Value", "Legal Terms"]]
            except KeyError:
                continue

            key_item_1["Document Name 1"] = document_name_1
            key_item_1["Key Item 1"] = key_name_1

            key_item_2["Document Name 2"] = document_name_2
            key_item_2["Key Item 2"] = key_name_2

            merged_key_items = pd.concat(
                [key_item_1.reset_index(drop=True), key_item_2.reset_index(drop=True)],
                axis=1,
                ignore_index=True,
            )

            merged_key_items["Project"] = project_row["site-lease"]

            merged_key_items.columns = [
                "Value 1",
                "Legal Terms 1",
                "Document Name 1",
                "Key Item 1",
                "Value 2",
                "Legal Terms 2",
                "Document Name 2",
                "Key Item 2",
                "Project",
            ]

            # Append the merged key items to the merged data DataFrame
            merged_data = merged_data._append(merged_key_items)
    # Save the merged data to a CSV file
    merged_data.to_csv("merged_data.csv", index=False)


if __name__ == "__main__":
    main()
