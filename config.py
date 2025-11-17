import os

class Config:
    SECRET_KEY = 'dev-secret-key-change-later'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tour_manager.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')

    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    UPLOAD_FOLDER = 'static/uploads'
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}

    QR_CODE_FOLDER = 'static/qr'
    QR_CODE_SIZE = 300

    PERMANENT_SESSION_LIFETIME = 604800