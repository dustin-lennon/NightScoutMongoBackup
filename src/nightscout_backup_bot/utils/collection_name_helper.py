"""
Helper for mapping display collection names to internal MongoDB collection names.
"""

COLLECTION_NAME_MAP = {
    "Entries": "entries",
    "Device Status": "devicestatus",
    "Treatments": "treatments",
    # Add more mappings as needed
}


def get_internal_collection_name(readable_name: str) -> str:
    """
    Map a display name to its internal MongoDB collection name.
    Returns the internal name, or the original if not found.
    """
    return COLLECTION_NAME_MAP.get(readable_name, readable_name)
