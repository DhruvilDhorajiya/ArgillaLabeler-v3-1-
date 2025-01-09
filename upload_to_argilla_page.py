import streamlit as st
import pandas as pd
import argilla as rg
import json
from labeling_page import format_value  # Import the existing format_value function

def convert_to_string(value):
    """Convert any value to a string representation suitable for Argilla"""
    if isinstance(value, (dict, list)):
        return format_value(value)  # Use your existing formatter
    return str(value) if value is not None else ""

def display_upload_to_argilla_page():
    st.title("Upload to Argilla")
    
    # 1) Load dataset and user selections from session state
    dataset = st.session_state.get("dataset", pd.DataFrame())
    selected_columns = st.session_state.get("selected_columns", [])
    questions = st.session_state.get("questions", [])

    # If no dataset or questions, warn user
    if dataset.empty or not questions:
        st.warning("No labeled dataset or questions found. Please ensure labeling is completed before uploading.")
        return
    
    
    # Extract the "text" key as the intended column name
    selected_texts = [col_info["text"] for col_info in selected_columns]

    # Check which user-selected columns actually exist in dataset
    recognized_cols = set(dataset.columns)            # e.g. {'doc_id','sentence','id',...}
    valid_cols = [col for col in selected_texts if col in recognized_cols]
    missing_cols = [col for col in selected_texts if col not in recognized_cols]

    # Warn if any columns are missing from the dataset
    if missing_cols:
        st.warning(f"Some columns are not found in the dataset: {missing_cols}")

    # If nothing valid is selected, warn. Otherwise preview what we do have
    if not valid_cols:
        st.warning("No columns selected or no valid columns found. Please select at least one valid column before uploading.")

    st.write("Labeled Dataset Preview:")
    st.write(dataset.head())  # Show entire dataset for reference

    guidelines = st.text_area("Write labeling guidelines:", value="")
    api_url = st.text_input("Argilla Server URL", value="https://dhruvil2004-my-argilla.hf.space/")
    api_key = st.text_input("Argilla API Key", type="password")
    dataset_name = st.text_input("Dataset Name", value="labeled_dataset")
    workspace_name = st.text_input("Workspace Name", value="argilla")

    # 3) Upload button to trigger Argilla upload
    if st.button("Upload to Argilla"):
        try:
            # Initialize Argilla client
            client = rg.Argilla(api_url=api_url, api_key=api_key)

            # 4) Build records containing just the selected columns + user annotations
            records = []
            for idx, row in dataset.iterrows():
                record = {}
                for col in valid_cols:
                    # Convert the value to string before adding to record
                    record[col] = convert_to_string(row[col])

                # Handle question-based annotations. Keep them in record["annotations"].
                annotations = {}
                for question in questions:
                    question_title = question["question_title"]
                    response = row.get(question_title)  # The labeled response
                    if response is not None:
                        annotations[question_title] = response
                record["annotations"] = annotations

                records.append(record)

            # 5) Build Argilla Settings: text fields + questions
            fields = [rg.TextField(name=col, title=col, use_markdown=False) for col in valid_cols]

            label_questions = []
            for question in questions:
                q_title = question["question_title"]
                q_type = question["question_type"]
                q_labels = question["labels"]
                q_desc = question["label_description"]

                if q_type == "Label":
                    # Single label
                    label_questions.append(
                        rg.LabelQuestion(name=q_title, labels=q_labels, description=q_desc)
                    )
                elif q_type == "Multi-label":
                    # Multiple labels
                    label_questions.append(
                        rg.MultiLabelQuestion(name=q_title, labels=q_labels, description=q_desc)
                    )
                elif q_type == "Rating":
                    # Numeric rating questions
                    label_questions.append(
                        rg.RatingQuestion(name=q_title, values=[1, 2, 3, 4, 5], description=q_desc)
                    )

            settings = rg.Settings(
                guidelines=guidelines,
                fields=fields,
                questions=label_questions
            )

            # 6) Create or retrieve dataset on Argilla
            dataset_for_argilla = rg.Dataset(name=dataset_name, workspace=workspace_name, settings=settings)
            dataset_for_argilla.create()

            # 7) Log records
            dataset_for_argilla.records.log(records)

            st.success("Data uploaded to Argilla successfully!")

        except Exception as e:
            st.error(f"Failed to upload to Argilla: {str(e)}")
