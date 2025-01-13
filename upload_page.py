import streamlit as st
import json
import pandas as pd
from typing import Dict, List, Union, Any
from collections import defaultdict

def get_path_value(data: Union[Dict, List], path: str) -> Any:
    """Get value from nested structure using dot notation path."""
    current = data
    try:
        # Handle array at root level
        if isinstance(current, list):
            if len(current) == 0:
                return None
            current = current[0]
            
        for part in path.split('.'):
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                # Try to get first non-null item for display
                current = next((item for item in current if item is not None), None)
                if isinstance(current, dict):
                    current = current.get(part)
            else:
                return None
            
            # Handle nested arrays
            if isinstance(current, list) and len(current) > 0:
                current = current[0]
                
        return current
    except (KeyError, IndexError, TypeError):
        return None

def flatten_json(data: Union[Dict, List], parent_key: str = '', sep: str = '.') -> List[str]:
    """Flatten a nested JSON structure and return paths to all leaf nodes."""
    paths = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            if isinstance(value, (dict, list)):
                if not value:  # Handle empty dict/list
                    paths.append(new_key)
                else:
                    paths.extend(flatten_json(value, new_key, sep))
            else:
                paths.append(new_key)
                
    elif isinstance(data, list):
        if not data:  # Handle empty list
            paths.append(parent_key)
        else:
            # Check all items in list to find all possible paths
            seen_paths = set()
            for item in data[:10]:  # Limit to first 10 items for performance
                if isinstance(item, dict):
                    for key, value in item.items():
                        new_key = f"{parent_key}{sep}{key}" if parent_key else key
                        if new_key not in seen_paths:
                            seen_paths.add(new_key)
                            if isinstance(value, (dict, list)):
                                paths.extend(flatten_json(value, new_key, sep))
                            else:
                                paths.append(new_key)
                elif isinstance(item, list):
                    paths.extend(flatten_json(item, parent_key, sep))
                else:
                    paths.append(parent_key)
                    break
    else:
        paths.append(parent_key)
    
    return list(dict.fromkeys(paths))  # Remove duplicates while preserving order

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

def render_tree(tree: Dict[str, Any], json_data: Any, parent_path: str = "", level: int = 0) -> dict:
    """Recursively render the tree structure and return selected paths and metadata paths."""
    selected_paths = {"fields": set(), "metadata": set()}
    
    # Initialize toggle states in session state if not exists
    if "tree_toggles" not in st.session_state:
        st.session_state.tree_toggles = {}
    
    # Add temporary state for checkboxes if not exists
    if "temp_selected_paths" not in st.session_state:
        st.session_state.temp_selected_paths = set()
    if "temp_metadata_paths" not in st.session_state:
        st.session_state.temp_metadata_paths = set()
    
    for key, subtree in tree.items():
        current_path = f"{parent_path}.{key}" if parent_path else key
        indent = "&nbsp;" * (level * 4)
        
        if subtree is None:  # Leaf node
            sample_value = get_path_value(json_data, current_path)
            sample_display = str(sample_value)
            if len(sample_display) > 50:
                sample_display = sample_display[:47] + "..."
            
            col1, col2, col3 = st.columns([2, 0.5, 1])
            
            with col1:
                st.markdown(f"{indent}📄 {key} ({sample_display})", unsafe_allow_html=True)
            
            with col2:
                # Single checkbox for selection
                is_selected = st.checkbox(
                    "Select",
                    key=f"select_{current_path}",
                    value=current_path in (st.session_state.temp_selected_paths | st.session_state.temp_metadata_paths)
                )
            
            with col3:
                # Show radio buttons only if checkbox is selected
                if is_selected:
                    field_type = st.radio(
                        "Type",
                        options=["Display", "Metadata"],
                        key=f"type_{current_path}",
                        horizontal=True,
                        index=1 if current_path in st.session_state.temp_metadata_paths else 0,
                        label_visibility="collapsed"
                    )
                    
                    # Update paths based on radio selection
                    if field_type == "Display":
                        selected_paths["fields"].add(current_path)
                        selected_paths["metadata"].discard(current_path)
                        st.session_state.temp_selected_paths.add(current_path)
                        st.session_state.temp_metadata_paths.discard(current_path)
                    else:  # Metadata
                        selected_paths["metadata"].add(current_path)
                        selected_paths["fields"].discard(current_path)
                        st.session_state.temp_metadata_paths.add(current_path)
                        st.session_state.temp_selected_paths.discard(current_path)
                else:
                    # If checkbox is unchecked, remove from both paths
                    selected_paths["fields"].discard(current_path)
                    selected_paths["metadata"].discard(current_path)
                    st.session_state.temp_selected_paths.discard(current_path)
                    st.session_state.temp_metadata_paths.discard(current_path)
            
        else:  # Branch node
            # Rest of the branch node code remains the same
            toggle_key = f"toggle_{current_path}"
            if toggle_key not in st.session_state.tree_toggles:
                st.session_state.tree_toggles[toggle_key] = True
                
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                if st.button("📁" if st.session_state.tree_toggles[toggle_key] else "📂", key=f"btn_{toggle_key}"):
                    st.session_state.tree_toggles[toggle_key] = not st.session_state.tree_toggles[toggle_key]
            with col2:
                st.markdown(f"{indent}**{key}**", unsafe_allow_html=True)
            
            if st.session_state.tree_toggles[toggle_key]:
                child_paths = render_tree(subtree, json_data, current_path, level + 1)
                selected_paths["fields"].update(child_paths["fields"])
                selected_paths["metadata"].update(child_paths["metadata"])
    
    return selected_paths

def load_json_data(uploaded_file):
    """Load data from either JSON or JSONL file"""
    file_extension = uploaded_file.name.split(".")[-1].lower()
    
    if file_extension == "jsonl":
        content = uploaded_file.getvalue().decode("utf-8")
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        if not lines:
            raise Exception("JSONL file is empty")
        
        parsed_lines = [json.loads(line) for line in lines]
        
        # Validate JSONL consistency
        if not validate_jsonl_consistency(parsed_lines):
            st.warning("Warning: Inconsistent schema detected in JSONL file. Some fields might not be available for all entries.")
            
        return {"data": parsed_lines}
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
    # Add new session state for metadata columns
    if "metadata_columns" not in st.session_state:
        st.session_state.metadata_columns = []
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

            if st.button("Next"):
                if selected_paths["fields"] or selected_paths["metadata"]:
                    # Store display columns in selected_columns
                    st.session_state.selected_columns = [
                        {
                            "id": f"path_{path}",
                            "text": path,
                            "path": path,
                        }
                        for path in selected_paths["fields"]
                    ]
                    
                    # Store metadata columns separately
                    st.session_state.metadata_columns = [
                        {
                            "id": f"path_{path}",
                            "text": path,
                            "path": path,
                        }
                        for path in selected_paths["metadata"]
                    ]
                    
                    # Update temporary states
                    st.session_state.temp_selected_paths = selected_paths["fields"]
                    st.session_state.temp_metadata_paths = selected_paths["metadata"]
                    
                    st.session_state.page = 2
                    st.rerun()
                else:
                    st.warning("Please select at least one field before proceeding.")

            

        except json.JSONDecodeError:
            st.error("Invalid JSON or JSONL file.")
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.error(f"Error details: {type(e).__name__}")  # Additional error info

def validate_jsonl_consistency(lines: List[dict]) -> bool:
    """Validate that all JSONL entries have consistent schema."""
    if not lines:
        return True
        
    first_keys = set(_get_all_paths(lines[0]))
    
    for line in lines[1:10]:  # Check first 10 lines for performance
        current_keys = set(_get_all_paths(line))
        if current_keys != first_keys:
            return False
    return True

def _get_all_paths(obj: Union[Dict, List], parent_key: str = '') -> List[str]:
    """Helper function to get all paths in an object."""
    paths = []
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, (dict, list)):
                paths.extend(_get_all_paths(value, new_key))
            else:
                paths.append(new_key)
    elif isinstance(obj, list) and obj:
        paths.extend(_get_all_paths(obj[0], parent_key))
        
    return paths
