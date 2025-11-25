import logging

import streamlit as st

from src.pipelines.constants import AgreementType
from src.pipelines.project_preview_builder import ProjectPreviewBuilder
from src.user_interface.auth import check_password
from src.user_interface.file_handler import StreamlitFileHandler


logger = logging.getLogger(__name__)

if not check_password():
    st.stop()  # Do not continue if check_password is not True.
pipeline_finished: bool = False
st.title("Project Preview Builder")
agreement_type = st.selectbox(
    "Choose an agreement type", [aggr_type.value for aggr_type in AgreementType]
)
poison_pills_detection = st.checkbox(
    "Add poison pills detection to the project preview (approx. 15 minutes runtime)"
)
with st.form("project-preview-builder-form", clear_on_submit=True):
    uploaded_files = st.file_uploader(
        f"Upload {agreement_type} files here...",
        type=None,
        accept_multiple_files=True,
        key=None,
        help=None,
        on_change=None,
        args=None,
        kwargs=None,
        disabled=False,
        label_visibility="visible",
    )
    submitted = st.form_submit_button("Confirm and Built Project Preview")

    file_handler = StreamlitFileHandler(uploaded_files)
    file_paths = file_handler.save_files()

    project_preview_builder = ProjectPreviewBuilder(
        file_paths,  # type: ignore
        agreement_type=AgreementType(agreement_type),
        poison_pills_detection=poison_pills_detection,
    )

    if submitted and uploaded_files:
        with st.status("Building project preview..."):
            result = project_preview_builder.get_project_preview()
            st.write("Project Preview built successfully!")
            st.write("Here are the results:")
            if poison_pills_detection:
                st.dataframe(result.drop(columns=["Poison Pills Presented"]))
            else:
                st.dataframe(result)
            pipeline_finished = True

if pipeline_finished:
    file_name = "output.xlsx"
    project_preview_builder.save_project_preview_to_excel(file_name=file_name)
    with open(file_name, "rb") as file:
        file_bytes = file.read()

        download_project_preview = st.download_button(
            label="Download Project Preview in Excel",
            data=file_bytes,
            file_name=f"{file_handler.document_names[0].split('.')[0]}"
            f"_project_preview.xlsx",
            mime="application/octet-stream",
        )
    if download_project_preview:
        st.rerun()
