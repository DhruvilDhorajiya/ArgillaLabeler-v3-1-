import streamlit as st
from upload_page import display_upload_page
from question_page import display_question_page
from labeling_page import display_labeling_page
from upload_to_argilla_page import display_upload_to_argilla_page

# st.set_page_config(layout="wide")

# Initialize session state if not present
if 'page' not in st.session_state:
    st.session_state.page = 1  # Start on page 1


# Main page display based on session state
if st.session_state.page == 1:
    #display_upload_to_argilla_page()
    display_upload_page()  # Show the upload and column selection page
elif st.session_state.page == 2:
    display_question_page()  # Show the question-adding page
elif st.session_state.page == 3:
    display_labeling_page()
elif st.session_state.page == 4:
    display_upload_to_argilla_page()

# if st.session_state.page == 1:
    
#     display_labeling_page()