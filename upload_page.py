import streamlit as st
import json
import pandas as pd
from typing import Dict, List, Union, Any
from collections import defaultdict

def get_path_value(data: Union[Dict, List], path: str) -> Any:
    """Get value from nested structure using dot notation path."""
    current = data
    if isinstance(current, list) and len(current) > 0:
        current = current[0]
        
    for part in path.split('.'):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current

def flatten_json(data: Union[Dict, List], parent_key: str = '', sep: str = '.') -> List[str]:
    """Flatten a nested JSON structure and return paths to all leaf nodes."""
    paths = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, (dict, list)):
                paths.extend(flatten_json(value, new_key, sep))
            else:
                paths.append(new_key)
    elif isinstance(data, list) and len(data) > 0:
        if isinstance(data[0], dict):
            for key, value in data[0].items():
                new_key = f"{parent_key}{sep}{key}" if parent_key else key
                if isinstance(value, (dict, list)):
                    paths.extend(flatten_json(value, new_key, sep))
                else:
                    paths.append(new_key)
        else:
            paths.append(parent_key)
    else:
        paths.append(parent_key)
    
    return paths

def organize_paths(paths: List[str], json_data: Any) -> Dict[str, Any]:
    """Organize paths into a proper hierarchical structure for display while maintaining order."""
    tree = {}
    
    # Helper function to get the original order of keys at each level
    def get_ordered_keys(data: Union[Dict, List], prefix: str = "") -> List[str]:
        if isinstance(data, dict):
            return [f"{prefix}{k}" if prefix else k for k in data.keys()]
        elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            return [f"{prefix}{k}" if prefix else k for k in data[0].keys()]
        return []

    # Build initial tree structure
    for path in paths:
        parts = path.split('.')
        current = tree
        for i, part in enumerate(parts):
            if i < len(parts) - 1:  # Not the last part
                if part not in current:
                    current[part] = {}
                current = current[part]
            else:  # Last part (leaf node)
                if part not in current:
                    current[part] = None

    # Function to sort dictionary keys based on original JSON order
    def sort_dict_by_json_order(d: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        if not isinstance(d, dict):
            return d

        # Get ordered keys for this level
        ordered_keys = get_ordered_keys(json_data, prefix)
        
        # Create new ordered dictionary
        ordered_dict = {}
        
        # First add keys that exist in original order
        for key in ordered_keys:
            key_without_prefix = key[len(prefix):] if prefix else key
            if key_without_prefix in d:
                ordered_dict[key_without_prefix] = sort_dict_by_json_order(
                    d[key_without_prefix], 
                    f"{prefix}{key_without_prefix}." if prefix else f"{key_without_prefix}."
                )
        
        # Then add any remaining keys that might not be in the original JSON
        for key in d:
            if key not in ordered_dict:
                ordered_dict[key] = sort_dict_by_json_order(
                    d[key],
                    f"{prefix}{key}." if prefix else f"{key}."
                )
        
        return ordered_dict

    # Sort the tree based on original JSON order
    return sort_dict_by_json_order(tree)

def render_tree(tree: Dict[str, Any], json_data: Any, parent_path: str = "", level: int = 0) -> set:
    """Recursively render the tree structure and return selected paths."""
    selected_paths = set()
    
    # Initialize toggle states in session state if not exists
    if "tree_toggles" not in st.session_state:
        st.session_state.tree_toggles = {}
    
    for key, subtree in tree.items():
        current_path = f"{parent_path}.{key}" if parent_path else key
        indent = "&nbsp;" * (level * 4)
        
        if subtree is None:  # Leaf node
            # Get sample value
            sample_value = get_path_value(json_data, current_path)
            sample_display = str(sample_value)
            if len(sample_display) > 50:
                sample_display = sample_display[:47] + "..."
            
            # Create indented checkbox
            if st.checkbox(
                f"{indent}📄 {key} ({sample_display})", 
                key=f"checkbox_{current_path}",
                value=any(col['path'] == current_path for col in st.session_state.selected_columns)
            ):
                selected_paths.add(current_path)
        else:  # Branch node
            # Create toggle for branch
            toggle_key = f"toggle_{current_path}"
            if toggle_key not in st.session_state.tree_toggles:
                st.session_state.tree_toggles[toggle_key] = True  # Start expanded
                
            # Display folder icon and toggle button
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.button("📁" if st.session_state.tree_toggles[toggle_key] else "📂", key=f"btn_{toggle_key}"):
                    st.session_state.tree_toggles[toggle_key] = not st.session_state.tree_toggles[toggle_key]
            with col2:
                st.markdown(f"{indent}**{key}**", unsafe_allow_html=True)
            
            # If expanded, show children
            if st.session_state.tree_toggles[toggle_key]:
                child_paths = render_tree(subtree, json_data, current_path, level + 1)
                selected_paths.update(child_paths)
    
    return selected_paths

def load_json_data(uploaded_file):
    """Load data from either JSON or JSONL file"""
    file_extension = uploaded_file.name.split(".")[-1].lower()
    
    if file_extension == "jsonl":
        content = uploaded_file.getvalue().decode("utf-8")
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if not lines:
            raise Exception("JSONL file is empty")
        
        first_line = json.loads(lines[0])
        return {"data": [first_line]}
    else:
        data = json.load(uploaded_file)
        if not isinstance(data, dict):
            data = {"data": [data]}
        elif "data" not in data:
            data = {"data": [data]}
        return data

def display_upload_page():
    # Initialize page state if not exists
    if "page" not in st.session_state:
        st.session_state.page = "upload"
    if "selected_columns" not in st.session_state:
        st.session_state.selected_columns = []
    if "json_data" not in st.session_state:
        st.session_state.json_data = None

    st.title("ArgillaLabeler")
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a JSON or JSONL file", type=["json", "jsonl"])

    if uploaded_file is not None:
        try:
            # Load and store JSON data
            json_data = load_json_data(uploaded_file)
            st.session_state.json_data = json_data

            # Get all possible paths and organize them into a tree
            paths = flatten_json(json_data)
            tree = organize_paths(paths, json_data)
            
            st.markdown("### Select Fields to Label")
            st.markdown("Expand sections and select the fields you want to include in your labeling task:")

            # Render the tree and get selected paths
            selected_paths = render_tree(tree, json_data)

            # Update session state with selected paths
            st.session_state.selected_columns = [
                {
                    "id": f"path_{path}",
                    "text": path,
                    "path": path
                }
                for path in selected_paths
            ]

            # Display current selection
            if st.session_state.selected_columns:
                st.markdown("### Selected Fields")
                for col in st.session_state.selected_columns:
                    # Display only the last part of the path
                    display_name = col['path'].split('.')[-1]
                    st.markdown(f"- {display_name}")

            # Navigation buttons
            col1, col2 = st.columns([1,1])
            with col1:
                if st.button("Save"):
                    if st.session_state.selected_columns:
                        st.success("Selected fields saved!")
                    else:
                        st.warning("Please select at least one field before saving.")

            with col2:
                if st.button("Next"):
                    if st.session_state.selected_columns:
                        st.session_state.page = 2
                        st.rerun()
                    else:
                        st.warning("Please select at least one field before proceeding.")

        except json.JSONDecodeError:
            st.error("Invalid JSON or JSONL file.")
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.error(f"Error details: {type(e).__name__}")  # Additional error info
