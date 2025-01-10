import streamlit as st
from labeling_page import create_dataframe_from_json

@st.fragment
def display_question_page():


    # Initialize session state variables
    if "questions" not in st.session_state:
        st.session_state.questions = []
    if "selected_question_type" not in st.session_state:
        st.session_state.selected_question_type = "Label"  # Default to Label

    # Initialize form-related session state variables
    if "form_data_title" not in st.session_state:
        st.session_state.form_data_title = ""
    if "form_data_description" not in st.session_state:
        st.session_state.form_data_description = ""
    if "form_data_labels" not in st.session_state:
        st.session_state.form_data_labels = ""
    if "labels_input_key" not in st.session_state:
        st.session_state.labels_input_key = "labels_input_0"
    
    # Get the JSON data and selected columns from session state
    json_data = st.session_state.get("json_data")  # Make sure to store the original JSON data
    selected_columns = st.session_state.get("selected_columns", [])

    # Create DataFrame if not already created
    if "dataset" not in st.session_state and json_data and selected_columns:
        st.session_state.dataset = create_dataframe_from_json(json_data, selected_columns)

    st.markdown("### Dataset Preview:")
    st.write(st.session_state.dataset.head(5))
    st.markdown("### Add Questions and Related Information")

    # Dropdown for selecting question type (outside the form)
    st.markdown("**Select question type:**")
    selected_question_type = st.selectbox(
        "Choose the type of question",
        ["Label", "Multi-label", "Rating"],
        index=["Label", "Multi-label", "Rating"].index(st.session_state.selected_question_type)
    )

    # Update session state when the user changes the question type
    st.session_state.selected_question_type = selected_question_type

    # Input fields for adding a question within a form
    question_title = st.text_input(
        "Describe Question Title (e.g., overall Quality):",
        value=st.session_state.form_data_title,
        key="question_title"
    )
    label_description = st.text_input(
        "Describe Question information (e.g., overall Quality of LLM Response):",
        value=st.session_state.form_data_description,
        key="label_description"
    )

    # Conditionally show labels input based on question type
    labels = []
    if st.session_state.selected_question_type in ["Label", "Multi-label"]:
        st.markdown(f"**Define possible {st.session_state.selected_question_type.lower()} options (comma-separated):**")
        labels_input_key = st.session_state.labels_input_key
        labels_input = st.text_input(
            "Example: Good, Average, Bad",
            value=st.session_state.form_data_labels,
            key=labels_input_key
        )
        labels = [label.strip() for label in labels_input.split(",") if label.strip()]
    
    submit_button = st.button("Add Question")

    # Handle form submission
    if submit_button:
        # Validation checks for form fields
        # if not label_description.strip():
        #     st.warning("Please provide a question description.")
        if not question_title.strip():
            st.warning("Please provide a question title.")
        elif st.session_state.selected_question_type in ["Label", "Multi-label"] and not labels:
            st.warning("Please define at least one label.")
        else:
            # Add question details to session state
            question_data = {
                'question_title': question_title,
                "label_description": label_description,
                "question_type": st.session_state.selected_question_type,
                "labels": labels if st.session_state.selected_question_type in ["Label", "Multi-label"] else None,
            }
            st.session_state.questions.append(question_data)

            st.success("Question added successfully!")
            
            # Clear form fields only after valid submission
            st.session_state.form_data_title = ""
            st.session_state.form_data_description = ""
            st.session_state.form_data_labels = ""

            # Update the `labels_input_key` dynamically to reset the text input
            st.session_state.labels_input_key = f"labels_input_{len(st.session_state.questions)}"

            # Optionally, re-run the page
            st.rerun()

    # If validation fails, retain the data in the form
    else:
        # Store the current form inputs in session state if user hasn't clicked submit
        st.session_state.form_data_title = question_title
        st.session_state.form_data_description = label_description
        st.session_state.form_data_labels = ", ".join(labels)

    # Display the list of added questions
    if st.session_state.questions:
        st.markdown("### Added Questions")
        for idx, question in enumerate(st.session_state.questions, start=1):
            st.markdown(f"**{idx}. Question title:** {question['question_title']}")
            st.markdown(f"**Question Description:** {question['label_description']}")
            st.markdown(f"**Question Type:** {question['question_type']}")
            if question['question_type'] in ["Label", "Multi-label"]:
                st.markdown(f"**Labels:** {', '.join(question['labels'])}")
            st.markdown("---")

    # Show "Next" button to navigate to the labeling page (third page)
    if st.button("Next"):
        if st.session_state.questions:
            st.session_state.page = 3  # Move to the labeling page
            st.rerun()  # Re-run the app to update page state
        else:
            st.warning("Please add at least one question before proceeding.")
