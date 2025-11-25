from typing import Any, Sequence

import pandas as pd
from google.cloud import documentai


def get_tables(document: documentai.Document) -> dict[int, list[Any]]:
    """Read the table output from the processor"""

    tables: dict[int, list[Any]] = {}
    text = document.text

    for page in document.pages:
        tables[page.page_number] = []
        for table in page.tables:
            columns_list = table_rows_as_string(table.header_rows, text)
            assert (
                len(columns_list) <= 1
            ), "Tables with multiple header rows are not supported"
            columns = columns_list[0] if columns_list else None
            rows = table_rows_as_string(table.body_rows, text)
            table = pd.DataFrame(rows, columns=columns)
            tables[page.page_number].append(table)

    return tables


def get_form_fields(document: documentai.Document) -> dict[int, dict[Any, Any]]:
    """Read the form fields output from the processor"""

    form_fields: dict[int, dict[Any, Any]] = {}
    text = document.text

    for page in document.pages:
        form_fields[page.page_number] = {}
        for field in page.form_fields:
            name = layout_to_text(field.field_name, text).strip()
            value = layout_to_text(field.field_value, text).strip()
            form_fields[page.page_number][name] = value

    return form_fields


def table_rows_as_string(
    table_rows: Sequence[documentai.Document.Page.Table.TableRow], text: str
) -> list[list[str]]:
    """Convert table rows to a string"""
    rows = []
    for table_row in table_rows:
        row = []
        for cell in table_row.cells:
            cell_text = layout_to_text(cell.layout, text)
            row.append(repr(cell_text.strip()))
        rows.append(row)
    return rows


def layout_to_text(layout: documentai.Document.Page.Layout, text: str) -> str:
    """
    Document AI identifies text in different parts of the document by their
    offsets in the entirety of the document"s text. This function converts
    offsets to a string.
    """
    # If a text segment spans several lines, it will
    # be stored in different text segments.
    return "".join(
        text[int(segment.start_index) : int(segment.end_index)]
        for segment in layout.text_anchor.text_segments
    )


def dataframe_to_string(df: pd.DataFrame) -> str:
    """Converts a dataframe to a string"""
    # Get the number of rows and columns
    num_rows, num_cols = df.shape

    # Create the header string
    header_str = "Table with {} columns and {} rows:\nColumns:\n".format(
        num_cols, num_rows
    )
    header_str += " | ".join(df.columns) + " |\n"

    # Create the body string
    body_str = "Table body data:\n"
    for _, row in df.iterrows():
        body_str += " | ".join(row.values.astype(str)) + " |\n"

    # Combine the header and body strings
    result_str = header_str + body_str

    return result_str


def dict_to_string(d: dict[Any, Any]) -> str:
    """Converts a dictionary to a string"""
    output = f"{len(d)} form field(s):\n"
    for key, value in d.items():
        output += f"    * '{key}': '{value}'\n"
    return output
