from flask import request, jsonify, after_this_request
from app.ai_model import bp
from app.utils.metadata_utils import extract_metadata_from_form, validate_metadata, extract_metadata, update_metadata_fields
from app.merkle_tree import build_tree, read_leaves_from_file, verify_model_integrity
from werkzeug.utils import secure_filename
import boto3
import os
from botocore.exceptions import NoCredentialsError
from sqlalchemy.exc import IntegrityError
from config import Config
from app.models.modelmetadata import ModelMetadata
from app.extensions import db
from flask import  send_file
import time



s3_client = boto3.client(
    's3',
    aws_access_key_id=Config.AWS_ACCESS_KEY,
    aws_secret_access_key=Config.AWS_SECRET_KEY,
    region_name=Config.AWS_REGION
)

@bp.route('/upload/', methods=['POST'])
def upload_model():
    if 'file' not in request.files:
        return jsonify({'error': "No file part of request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': "No Selected file"}), 400

    # Sanitize the file name
    original_filename = file.filename
    sanitized_filename = secure_filename(original_filename).replace(" ", "_")

    # Extract metadata from form using the utility function
    metadata = extract_metadata_from_form()

    # Validate required fields
    if not metadata['accuracy']:
        return jsonify({'error': "Accuracy is a required field and cannot be None."}), 400

    try:
        accuracy = float(metadata['accuracy'])
    except ValueError:
        return jsonify({'error': 'Accuracy must be a valid number.'}), 400

    version = request.form.get('version')
    if not version:
        return jsonify({'error': "Version is a required field and cannot be None."}), 400

    # Define the custom temporary directory path
    temp_dir = os.path.join(os.getcwd(), 'temp')
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Construct the full path for the temporary file
    temp_file_path = os.path.join(temp_dir, sanitized_filename)

    # Save the file temporarily with the sanitized file name
    file.save(temp_file_path)

    # Check if the file is saved properly
    if not os.path.exists(temp_file_path):
        return jsonify({'error': f"File {sanitized_filename} was not saved properly to {temp_file_path}"}), 500

    try:
        # Step 1: Read the leaves from the saved file
        leaves = read_leaves_from_file(temp_file_path)

        # Step 2: Generate Merkle Tree and save it to a file
        merkle_tree_file = os.path.join(temp_dir, f"{sanitized_filename}_merkle.tree")
        root = build_tree(leaves, merkle_tree_file)

        # Upload the file to S3
        s3_client.upload_file(temp_file_path, Config.S3_BUCKET, f"models/{sanitized_filename}_v{version}")
        s3_url = f"https://{Config.S3_BUCKET}.s3.{Config.AWS_REGION}.amazonaws.com/models/{sanitized_filename}_v{version}"

        # Optional Step: Upload the Merkle Tree file to S3
        s3_client.upload_file(merkle_tree_file, Config.S3_BUCKET, f"merkle_trees/{sanitized_filename}_v{version}_merkle.tree")

        # Create a new metadata record
        new_metadata = ModelMetadata(
            model_name=sanitized_filename,
            version=version,
            description=metadata.get('description', ''),
            accuracy=accuracy,
            s3_url=s3_url,
            merkle_root=root.hashValue,
            change_log=metadata.get('change_log', '')
        )

        db.session.add(new_metadata)
        db.session.commit()

        # Remove temporary files after uploading
        os.remove(temp_file_path)
        os.remove(merkle_tree_file)

        return jsonify({
            'message': f'{sanitized_filename} uploaded successfully!',
            's3_url': s3_url,
            'merkle_root': root.hashValue
        }), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'A database integrity error occurred. Please check for duplicate entries or other constraints.'}), 400
    except NoCredentialsError:
        return jsonify({'error': 'Credentials not available'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@bp.route('/models/', methods=['GET'])
def list_models():
    try:
        # Step 1: Query the database for all model metadata entries
        metadata_list = ModelMetadata.query.all()

        print(metadata_list, "metadataList")
        
        # Step 2: Convert each model metadata entry to a dictionary
        models = [model.to_dict() for model in metadata_list]
        
        # Step 3: Return the list of models as a JSON response
        return jsonify({'models': models}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    


@bp.route('/download/<model_name>/<version>', methods=['GET'])
def download_model(model_name, version):
    try:
        # Step 1: Check if the model with the given name and version exists in the database
        model_metadata = ModelMetadata.query.filter_by(model_name=model_name, version=version).first()
        
        if not model_metadata:
            return jsonify({'error': f'Model {model_name} with version {version} not found in the registry.'}), 404
        
        # Step 2: Fetch the S3 URL and Merkle root from the database metadata
        s3_url = model_metadata.s3_url
        stored_merkle_root = model_metadata.merkle_root

        # Step 3: Define the temporary local filename for the model download
        sanitized_filename = f"{model_name}_v{version}"
        temp_dir = os.path.join(os.getcwd(), 'temp')

        # Create the directory if it does not exist
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        local_filename = os.path.join(temp_dir, sanitized_filename)

        # Step 4: Download the model file from S3 to the temporary location
        s3_key = f"models/{sanitized_filename}"
        s3_client.download_file(Config.S3_BUCKET, s3_key, local_filename)

        # Step 5: Verify the integrity of the downloaded file using the stored Merkle root
        is_verified = verify_model_integrity(local_filename, stored_merkle_root)

        if not is_verified:
            # If the verification fails, delete the local file and return an error
            os.remove(local_filename)
            return jsonify({'error': 'Model integrity verification failed. The file might be corrupted.'}), 400

        # Schedule the file to be deleted after the response is sent
        @after_this_request
        def cleanup(response):
            try:
                # Delay to ensure the file is no longer being used
                time.sleep(1)
                os.remove(local_filename)
                print(f"File {local_filename} successfully deleted.")
            except Exception as e:
                print(f"Error deleting file: {e}")
            return response

        # Step 6: If verification is successful, return the file to the user as a downloadable attachment
        return send_file(local_filename, as_attachment=True, download_name=sanitized_filename)
    
    except NoCredentialsError:
        return jsonify({'error': 'Credentials not available to access S3'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/models/<model_name>/versions', methods=['POST'])
def add_new_version(model_name):
    try:
        # Check if a file is provided in the request
        if 'file' not in request.files:
            return jsonify({'error': "No file part of request"}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': "No file selected."}), 400

        # Extract metadata from form data
        metadata = extract_metadata_from_form()

        # Validate required fields in the metadata
        validation_error = validate_metadata(metadata, required_fields=['version', 'accuracy'])
        if validation_error:
            return jsonify({'error': validation_error}), 400

        version = metadata['version']
        accuracy = metadata['accuracy']

        # Check if a model with the same name exists
        existing_model = ModelMetadata.query.filter_by(model_name=model_name).first()
        if not existing_model:
            return jsonify({'error': f"Model '{model_name}' does not exist. Please create the model first."}), 400

        # Check if the version already exists for the given model
        existing_version = ModelMetadata.query.filter_by(model_name=model_name, version=version).first()
        if existing_version:
            return jsonify({'error': f"Version '{version}' already exists for model '{model_name}'."}), 400

        # Sanitize the file name
        original_filename = file.filename
        sanitized_filename = secure_filename(f"{model_name}_v{version}")

        # Define the custom temporary directory path
        temp_dir = os.path.join(os.getcwd(), 'temp')

        # Create the directory if it does not exist
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)

        # Construct the full path for the temporary file
        temp_file_path = os.path.join(temp_dir, sanitized_filename)

        # Save the file temporarily with the sanitized file name
        file.save(temp_file_path)

        # Check if the file is saved properly
        if not os.path.exists(temp_file_path):
            return jsonify({'error': f"File {sanitized_filename} was not saved properly to {temp_file_path}"}), 500

        # Step 1: Read the leaves from the saved file
        leaves = read_leaves_from_file(temp_file_path)

        # Step 2: Generate Merkle Tree and save it to a file
        merkle_tree_file = os.path.join(temp_dir, f"{sanitized_filename}_merkle.tree")
        root = build_tree(leaves, merkle_tree_file)

        # Step 3: Upload the model file to S3 with the versioned path
        s3_key = f"models/{model_name}_v{version}"
        s3_client.upload_file(temp_file_path, Config.S3_BUCKET, s3_key)
        s3_url = f"https://{Config.S3_BUCKET}.s3.{Config.AWS_REGION}.amazonaws.com/{s3_key}"

        # Step 4: Upload the Merkle Tree file to S3
        s3_client.upload_file(merkle_tree_file, Config.S3_BUCKET, f"merkle_trees/{sanitized_filename}_merkle.tree")

        # Step 5: Create a new metadata record for the version
        new_metadata = ModelMetadata(
            model_name=model_name,
            version=version,
            description=metadata.get('description', ''),
            accuracy=float(accuracy),
            s3_url=s3_url,
            merkle_root=root.hashValue,
            change_log=metadata.get('change_log', '')  # Adding the change_log to metadata
        )

        db.session.add(new_metadata)
        db.session.commit()

        # Remove temporary files after uploading
        os.remove(temp_file_path)
        os.remove(merkle_tree_file)

        return jsonify({
            'message': f'New version {version} for model {model_name} uploaded successfully!',
            's3_url': s3_url,
            'merkle_root': root.hashValue
        }), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'A database integrity error occurred. Please check for duplicate entries or other constraints.'}), 400
    except NoCredentialsError:
        return jsonify({'error': 'Credentials not available'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/models/<model_name>/versions/<version>', methods=['PUT'])
def update_version_metadata(model_name, version):
    try:
        # Step 1: Check if the model with the given name and version exists in the database
        model_metadata = ModelMetadata.query.filter_by(model_name=model_name, version=version).first()
        
        if not model_metadata:
            return jsonify({'error': f'Model {model_name} with version {version} not found in the registry.'}), 404

        # Step 2: Extract metadata fields from the request
        metadata = extract_metadata()
        
        # Step 3: Validate the extracted metadata fields
        validation_error = validate_metadata(metadata, required_fields=[])
        if validation_error:
            return jsonify({'error': validation_error}), 400

        # Step 4: Update the metadata fields of the model
        try:
            update_metadata_fields(model_metadata, metadata)
        except ValueError as e:
            return jsonify({'error': str(e)}), 400

        # Step 5: Commit the changes to the database
        db.session.commit()

        return jsonify({
            'message': f'Metadata for model {model_name} version {version} updated successfully.',
            'updated_metadata': model_metadata.to_dict()
        }), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'A database integrity error occurred. Please check the input values or constraints.'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# fetch metadata and download link for a specific model version.
@bp.route('/models/<model_name>/versions/<version>', methods=['GET'])
def get_model_version(model_name, version):
    try:
        # Check if the model with the given name and version exists
        model_metadata = ModelMetadata.query.filter_by(model_name=model_name, version=version).first()
        
        if not model_metadata:
            return jsonify({'error': f'Model {model_name} with version {version} not found in the registry.'}), 404

        # Return the metadata and download link
        return jsonify({
            'model_name': model_metadata.model_name,
            'version': model_metadata.version,
            'description': model_metadata.description,
            'accuracy': model_metadata.accuracy,
            's3_url': model_metadata.s3_url,
            'merkle_root': model_metadata.merkle_root,
            'upload_date': model_metadata.upload_date,
            'change_log': model_metadata.change_log
        }), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

# Lists all versions of a specific model along with their metadata.
@bp.route('/models/<model_name>/versions', methods=['GET'])
def list_model_versions(model_name):
    try:
        # Query for all versions of the given model
        versions = ModelMetadata.query.filter_by(model_name=model_name).all()
        
        if not versions:
            return jsonify({'error': f'No versions found for model {model_name}.'}), 404

        # Create a list of metadata for each version
        version_list = []
        for version in versions:
            version_list.append({
                'version': version.version,
                'description': version.description,
                'accuracy': version.accuracy,
                's3_url': version.s3_url,
                'merkle_root': version.merkle_root,
                'upload_date': version.upload_date,
                'change_log': version.change_log
            })

        # Return the list of versions and their metadata
        return jsonify({'model_name': model_name, 'versions': version_list}), 200
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    

@bp.route('/models/<model_name>/versions/<version>/deprecate', methods=['PATCH'])
def deprecate_model_version(model_name, version):
    try:
        # Check if the model with the given name and version exists
        model_metadata = ModelMetadata.query.filter_by(model_name=model_name, version=version).first()
        
        if not model_metadata:
            return jsonify({'error': f'Model {model_name} with version {version} not found in the registry.'}), 404

        # Mark the version as deprecated
        model_metadata.deprecated = True
        db.session.commit()

        return jsonify({
            'message': f'Model {model_name} version {version} marked as deprecated.',
            'updated_metadata': model_metadata.to_dict()
        }), 200
    
    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'A database integrity error occurred. Please check the input values or constraints.'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500




