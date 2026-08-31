import os


class Config:
    """Application configuration loaded from environment variables."""

    def __init__(self) -> None:
        """
        Read all required settings from the process environment.

        :return: None
        """
        self.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
        self.database_uri = (
            f"postgresql+psycopg2://{os.environ['DATABASE_USER']}:{os.environ['DATABASE_PASS']}"
            f"@{os.environ['DATABASE_HOST']}:{os.environ['DATABASE_PORT']}/{os.environ['DATABASE_NAME']}"
        )
        self.max_content_length = 16 * 1024 * 1024
        self.google_client_id = os.environ["GOOGLE_CLIENT_ID"]
        self.google_client_secret = os.environ["GOOGLE_CLIENT_SECRET"]
        self.images_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "images")
        self.models_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "models")
