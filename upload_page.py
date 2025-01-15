import streamlit as st
import json
import pandas as pd
from typing import Dict, List, Union, Any
from collections import defaultdict

def get_path_value(data: Union[Dict, List], path: str) -> Any:
    """Get value from nested structure using dot notation path."""
    try:
        current = data
        parts = path.split('.')
        
        # Special handling for 'data' at the root
        if parts[0] == 'data' and isinstance(current.get('data'), list):
            current = current['data']
            # For preview, just show first item
            if len(parts) > 1 and current:
                current = current[0]
            parts = parts[1:]
        
        # Navigate through the path
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                # If we're looking at a list, we want to:
                # 1. Show all values for actual data processing
                # 2. Show first value for preview
                preview_mode = True  # Set this based on context
                if preview_mode and current:
                    current = current[0].get(part) if isinstance(current[0], dict) else None
                else:
                    return [item.get(part) if isinstance(item, dict) else None for item in current]
            else:
                return None
                
        return current
    except (KeyError, IndexError, AttributeError):
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
    """Recursively render the tree structure."""
    selected_paths = {
        "fields": [],
        "metadata": []
    }
    
    for key, subtree in tree.items():
        current_path = f"{parent_path}.{key}" if parent_path else key
        indent = "&nbsp;" * (level * 4)
        
        if subtree is None:  # Leaf node
            value = get_path_value(json_data, current_path)
            
            col1, col2, col3 = st.columns([2, 0.5, 1])
            
            with col1:
                # Remove the sample display, just show the key
                st.markdown(f"{indent}📄 {key}", unsafe_allow_html=True)
            
            with col2:
                is_selected = st.checkbox(
                    "Select",
                    key=f"select_{current_path}",
                    value=current_path in (st.session_state.temp_selected_paths | st.session_state.temp_metadata_paths)
                )
            
            with col3:
                if is_selected:
                    field_type = st.radio(
                        "Type",
                        options=["Display", "Metadata"],
                        key=f"type_{current_path}",
                        horizontal=True,
                        index=1 if current_path in st.session_state.temp_metadata_paths else 0,
                        label_visibility="collapsed"
                    )
                    
                    # Update selected paths while maintaining order
                    if field_type == "Display":
                        if current_path not in selected_paths["fields"]:
                            selected_paths["fields"].append(current_path)
                        if current_path in selected_paths["metadata"]:
                            selected_paths["metadata"].remove(current_path)
                        st.session_state.temp_selected_paths.add(current_path)
                        st.session_state.temp_metadata_paths.discard(current_path)
                    else:
                        if current_path not in selected_paths["metadata"]:
                            selected_paths["metadata"].append(current_path)
                        if current_path in selected_paths["fields"]:
                            selected_paths["fields"].remove(current_path)
                        st.session_state.temp_metadata_paths.add(current_path)
                        st.session_state.temp_selected_paths.discard(current_path)
                else:
                    # Clear selections if unchecked
                    if current_path in selected_paths["fields"]:
                        selected_paths["fields"].remove(current_path)
                    if current_path in selected_paths["metadata"]:
                        selected_paths["metadata"].remove(current_path)
                    st.session_state.temp_selected_paths.discard(current_path)
                    st.session_state.temp_metadata_paths.discard(current_path)

        else:  # Branch node
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
                # Extend lists instead of updating sets
                for path in child_paths["fields"]:
                    if path not in selected_paths["fields"]:
                        selected_paths["fields"].append(path)
                for path in child_paths["metadata"]:
                    if path not in selected_paths["metadata"]:
                        selected_paths["metadata"].append(path)
    
    return selected_paths

def load_json_data(uploaded_file):
    """Load data from either JSON or JSONL file and normalize into a consistent format."""
    try:
        file_extension = uploaded_file.name.split(".")[-1].lower()
        
        if file_extension == "jsonl":
            # Read JSONL file line by line
            content = uploaded_file.getvalue().decode("utf-8")
            lines = [line.strip() for line in content.split("\n") if line.strip()]
            
            if not lines:
                st.error("JSONL file is empty")
                return None
            
            # Parse each line as JSON
            records = []
            for line in lines:
                try:
                    record = json.loads(line)
                    records.append(record)
                except json.JSONDecodeError:
                    continue  # Skip invalid lines
            
            if not records:
                st.error("No valid JSON records found in JSONL file")
                return None
            
            # Normalize the data structure
            return {"data": records}
            
        else:  # JSON file
            data = json.load(uploaded_file)
            
            # Normalize the data structure
            if isinstance(data, list):
                return {"data": data}
            elif isinstance(data, dict):
                if 'data' in data and isinstance(data['data'], list):
                    return data
                elif 'data' in data:
                    return {"data": [data['data']]}
                else:
                    return {"data": [data]}
            else:
                st.error("Invalid JSON structure")
                return None
                
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

def validate_jsonl_consistency(records: List[dict]) -> bool:
    """Check if all records in JSONL have similar structure."""
    if not records:
        return True
    
    # Get structure of first record
    first_keys = set(flatten_json(records[0]))
    
    # Check first few records for consistency
    for record in records[1:min(10, len(records))]:
        current_keys = set(flatten_json(record))
        if not (first_keys & current_keys):  # If no common keys
            return False
    return True

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
    # Initialize tree toggles
    if "tree_toggles" not in st.session_state:
        st.session_state.tree_toggles = {}
    # Initialize temporary states for selections
    if "temp_selected_paths" not in st.session_state:
        st.session_state.temp_selected_paths = set()
    if "temp_metadata_paths" not in st.session_state:
        st.session_state.temp_metadata_paths = set()

    st.title("ArgillaLabeler")
    
    # File uploader
    uploaded_file = st.file_uploader("Choose a JSON or JSONL file", type=["json", "jsonl"])

    if uploaded_file is not None:
        try:
            # Load and store JSON/JSONL data
            json_data = load_json_data(uploaded_file)
            
            if json_data is None:
                return
                
            # Validate data consistency for JSONL
            if uploaded_file.name.endswith('.jsonl'):
                if not validate_jsonl_consistency(json_data.get('data', [])):
                    st.warning("Warning: Records in JSONL file have inconsistent structure. Some fields might not be available for all records.")
            
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
                    # Store display columns in selected_columns maintaining order
                    st.session_state.selected_columns = [
                        {
                            "id": f"path_{path}",
                            "text": path,
                            "path": path,
                        }
                        for path in selected_paths["fields"]  # fields are already in order
                    ]
                    
                    # Store metadata columns separately maintaining order
                    st.session_state.metadata_columns = [
                        {
                            "id": f"path_{path}",
                            "text": path,
                            "path": path,
                        }
                        for path in selected_paths["metadata"]  # metadata are already in order
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
