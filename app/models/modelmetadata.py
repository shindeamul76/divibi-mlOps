from app.extensions import db

class ModelMetadata(db.Model):
    __tablename__ = 'model_metadata'  # Define a table name if you want

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(120), nullable=False, index=True)  # Added index
    version = db.Column(db.String(50), nullable=False, index=True)      # Added index
    description = db.Column(db.String(255))
    accuracy = db.Column(db.Float)
    s3_url = db.Column(db.String(255), nullable=False)
    merkle_root = db.Column(db.String(64), nullable=False)
    change_log = db.Column(db.Text)
    deprecated = db.Column(db.Boolean, default=False)
    upload_date = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Define a composite unique constraint for model_name and version
    __table_args__ = (
        db.UniqueConstraint('model_name', 'version', name='unique_model_version'),
    )

    def to_dict(self):
        return {
            'model_name': self.model_name,
            'version': self.version,
            'description': self.description,
            'accuracy': self.accuracy,
            's3_url': self.s3_url,
            'merkle_root': self.merkle_root,
            'change_log': self.change_log,
            'deprecated': self.deprecated,
            'upload_date': self.upload_date,
        }
