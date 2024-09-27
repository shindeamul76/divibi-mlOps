from flask import request

def extract_metadata_from_form():
    """
    Extracts metadata fields from a multipart/form-data request and returns them as a dictionary.
    If a field is not present in the request, it will be set to None.
    """
    # Define required and optional metadata fields
    required_fields = ['accuracy']
    optional_fields = ['description', 'change_log']

    # Extract all fields
    metadata = {}
    for field in required_fields + optional_fields:
        metadata[field] = request.form.get(field, None)
    
    return metadata


def extract_metadata():
    """
    Extracts metadata fields from the request and returns them as a dictionary.
    If a field is not present in the request, it will be set to None.
    """
    # Define required and optional metadata fields
    required_fields = ['accuracy']
    optional_fields = ['description', 'change_log']

    # Extract all fields
    metadata = {}
    for field in required_fields + optional_fields:
        metadata[field] = request.json.get(field, None)
    
    return metadata


from flask import request

def extract_metadata_from_form():
    """
    Extracts metadata fields from the request form and returns them as a dictionary.
    If a field is not present in the request, it will be set to None.
    """
    # Define required and optional metadata fields
    metadata_fields = ['description', 'accuracy', 'version', 'change_log']
    
    # Extract metadata fields from the form
    metadata = {}
    for field in metadata_fields:
        metadata[field] = request.form.get(field, None)
    
    return metadata

def validate_metadata(metadata, required_fields):
    """
    Validates the required metadata fields and checks for any missing or invalid fields.
    :param metadata: The metadata dictionary to be validated.
    :param required_fields: A list of fields that are required.
    :return: An error message if validation fails, otherwise None.
    """
    for field in required_fields:
        if field not in metadata or metadata[field] is None:
            return f"'{field}' is a required field and cannot be None."
        
        if field == 'accuracy':
            try:
                float(metadata[field])
            except ValueError:
                return "'accuracy' must be a valid number."
    
    return None



def update_metadata_fields(model_metadata, metadata):
    """
    Updates the fields of the given model_metadata object based on the provided metadata dictionary.
    :param model_metadata: The ModelMetadata object to be updated.
    :param metadata: A dictionary containing the new metadata values.
    """
    # Define required fields for validation
    required_fields = ['accuracy']

    # Check for required fields in metadata
    for field in required_fields:
        if metadata[field] is None:
            raise ValueError(f"{field} is a required field and cannot be None or missing.")

    # Update fields in model_metadata
    for key, value in metadata.items():
        if value is not None:
            if key == 'accuracy':
                try:
                    setattr(model_metadata, key, float(value))
                except ValueError:
                    raise ValueError(f"{key} must be a valid number.")
            else:
                setattr(model_metadata, key, value)
