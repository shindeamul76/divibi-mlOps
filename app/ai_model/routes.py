from flask import request, jsonify, after_this_request
from app.ai_model import bp
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
        return jsonify({'error': "No file part in the request"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': "No file selected"}), 400

    version = request.form.get('version')
    description = request.form.get('description', '')
    accuracy = request.form.get('accuracy')

    if not version or not accuracy:
        return jsonify({'error': "Version and accuracy must be specified"}), 400

    # Sanitize the file name and ensure no spaces or unsafe characters
    original_filename = file.filename
    sanitized_filename = secure_filename(original_filename).replace(" ", "_")

    # Define the custom temporary directory path
    temp_dir = os.path.join(os.getcwd(), 'temp')

    # Create the directory if it does not exist
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)

    # Construct the full path for the temporary file with versioning
    temp_file_path = os.path.join(temp_dir, f"{sanitized_filename}_v{version}")
    
    try:
        # Save the file temporarily with the sanitized file name
        file.save(temp_file_path)

        # Check if the file is saved properly
        if not os.path.exists(temp_file_path):
            return jsonify({'error': f"File {sanitized_filename} was not saved properly to {temp_file_path}"}), 500

        # Step 1: Read the leaves from the saved file
        leaves = read_leaves_from_file(temp_file_path)

        # Step 2: Generate Merkle Tree and save it to a file
        merkle_tree_file = os.path.join(temp_dir, f"{sanitized_filename}_v{version}_merkle.tree")
        root = build_tree(leaves, merkle_tree_file)

        # Step 3: Upload the model file to S3 with versioning in the file name
        s3_key = f"models/{sanitized_filename}_v{version}"
        s3_client.upload_file(temp_file_path, Config.S3_BUCKET, s3_key)
        s3_url = f"https://{Config.S3_BUCKET}.s3.{Config.AWS_REGION}.amazonaws.com/{s3_key}"

        # Step 4: Upload the Merkle Tree file to S3
        merkle_s3_key = f"merkle_trees/{sanitized_filename}_v{version}_merkle.tree"
        s3_client.upload_file(merkle_tree_file, Config.S3_BUCKET, merkle_s3_key)

        # Step 5: Create a new metadata record in the database with version information
        new_metadata = ModelMetadata(
            model_name=sanitized_filename,
            version=version,
            description=description,
            accuracy=float(accuracy),
            s3_url=s3_url,
            merkle_root=root.hashValue
        )

        db.session.add(new_metadata)
        db.session.commit()

        # Remove temporary files after successful upload
        os.remove(temp_file_path)
        os.remove(merkle_tree_file)

        return jsonify({
            'message': f'{sanitized_filename} (version {version}) uploaded successfully!',
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

    finally:
        # Ensure temporary files are cleaned up even if an error occurs
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        if os.path.exists(merkle_tree_file):
            os.remove(merkle_tree_file)

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
