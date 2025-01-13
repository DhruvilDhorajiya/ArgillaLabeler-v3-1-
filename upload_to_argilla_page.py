import streamlit as st
import pandas as pd
import argilla as rg
import json
from labeling_page import format_value  # If you have a custom format_value function

def convert_to_string(value):
    """Convert any value to a string representation suitable for Argilla"""
    if isinstance(value, (dict, list)):
        return format_value(value)  # Use your existing formatter
    return str(value) if value is not None else ""

def get_value_from_path(data: dict, path: str):
    """Extract value from nested JSON using a simple dot-notation path."""
    try:
        current = data
        for part in path.split('.'):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and current:
                # If it's a list, assume we want the first item in that list
                current = current[0].get(part)
            else:
                return None
        return current
    except (KeyError, IndexError, AttributeError):
        return None

def display_upload_to_argilla_page():
    st.title("Upload to Argilla")
    
    # 1) Load your data from streamlit session
    dataset = st.session_state.get("dataset", pd.DataFrame())
    selected_columns = st.session_state.get("selected_columns", [])
    # We assume metadata_columns is a list of dicts: [{'text': 'doc_type', 'path': 'doc_type'}, ...]
    metadata_columns = st.session_state.get("metadata_columns", [])
    questions = st.session_state.get("questions", [])
    # The original JSON data you want to pull metadata from
    json_data = st.session_state.get("json_data", {}).get("data", [])

    if dataset.empty or not questions:
        st.warning("No labeled dataset or questions found. Please ensure labeling is completed before uploading.")
        return

    # Separate user-selected columns that show in the labeling UI (from your Pandas dataset)
    recognized_cols = set(dataset.columns)
    field_cols = [col_def["text"] for col_def in selected_columns if col_def["text"] in recognized_cols]
    
    # Basic validation
    missing_field_cols = [col_def["text"] for col_def in selected_columns if col_def["text"] not in recognized_cols]
    if missing_field_cols:
        st.warning(f"Some columns are not found in the dataset: {missing_field_cols}")

    if not field_cols and not metadata_columns:
        st.warning("No valid columns found. Please select at least one field or metadata column before uploading.")
    
    st.write("Labeled Dataset Preview:")
    st.write(dataset.head())  # Show entire dataset for reference

    guidelines = st.text_area("Write labeling guidelines:", value="")
    api_url = st.text_input("Argilla Server URL", value="https://dhruvil2004-my-argilla.hf.space/")
    api_key = st.text_input("Argilla API Key", type="password", 
                            value="0FzoksnKXf-4xYR6s6_nFYHyMbJ8s-rqGfj1IjRBPw5IkmhDa1KBzQ6cAb74-qd5BsBI6QKQ1lq749axTmet3_f2RSb-xoddBD2NgH5ld0g")
    dataset_name = st.text_input("Dataset Name", value="labeled_dataset")
    workspace_name = st.text_input("Workspace Name", value="argilla")

    if st.button("Upload to Argilla"):
        try:
            client = rg.Argilla(api_url=api_url, api_key=api_key)

            # 2) Create Argilla fields for the labeling UI
            fields = [
                rg.TextField(name=col, title=col, use_markdown=False)
                for col in field_cols
            ]

            # 3) Create metadata properties. We'll use TextMetadataProperty so any string is accepted.
            #    Each metadata_columns entry is assumed to look like {"text": "doc_type", "path": "doc_type"}.
            #    The "text" is what we'll use as Argilla's metadata name/title.
            # First collect all possible values for each metadata field
            metadata_values = {}
            for meta_def in metadata_columns:
                unique_values = set()
                for record in json_data:
                    # Remove 'data.' from the path since we're already inside data array
                    path = meta_def["path"].replace("data.", "")
                    value = get_value_from_path(record, path)
                    if value is not None:
                        unique_values.add(str(value))
                metadata_values[meta_def["text"]] = sorted(list(unique_values))

            print("Collected metadata values:", metadata_values)  # Debug print

            metadata_properties = [
                rg.TermsMetadataProperty(
                    name=meta_def["text"],  # Example: "doc_type"
                    title=meta_def["text"],
                    options=metadata_values[meta_def["text"]]  # Add the possible values
                )
                for meta_def in metadata_columns
            ]

            # 4) Build label questions from your Q&A
            label_questions = []
            for question in questions:
                q_title = question["question_title"]
                q_type = question["question_type"]
                q_labels = question["labels"]
                q_desc = question["label_description"]

                if q_type == "Label":
                    label_questions.append(
                        rg.LabelQuestion(name=q_title, labels=q_labels, description=q_desc)
                    )
                elif q_type == "Multi-label":
                    label_questions.append(
                        rg.MultiLabelQuestion(name=q_title, labels=q_labels, description=q_desc)
                    )
                elif q_type == "Rating":
                    label_questions.append(
                        rg.RatingQuestion(name=q_title, values=[1, 2, 3, 4, 5], description=q_desc)
                    )

            # 5) Argilla dataset settings
            settings = rg.Settings(
                guidelines=guidelines,
                fields=fields,
                questions=label_questions,
                metadata=metadata_properties
            )

            # 6) Build records. We'll match each row in the dataset with the corresponding JSON record by index.
            records = []
            for idx, row in dataset.iterrows():
                fields_dict = {
                    col: convert_to_string(row[col])
                    for col in field_cols
                }
                
                metadata_dict = {}
                if idx < len(json_data):
                    for meta_def in metadata_columns:
                        # Remove 'data.' from the path since we're already inside data array
                        path = meta_def["path"].replace("data.", "")
                        value = get_value_from_path(json_data[idx], path)
                        if value is not None:
                            metadata_dict[meta_def["text"]] = convert_to_string(value)

        
                record = rg.Record(
                    fields=fields_dict,
                    metadata=metadata_dict
                )
                records.append(record)

            # 7) Create or retrieve dataset on Argilla
            dataset_for_argilla = rg.Dataset(
                name=dataset_name,
                workspace=workspace_name,
                settings=settings
            )
            dataset_for_argilla.create()

            # 8) Log records
            dataset_for_argilla.records.log(records)

            st.success("Data uploaded to Argilla successfully!")

        except Exception as e:
            st.error(f"Failed to upload to Argilla: {str(e)}")
