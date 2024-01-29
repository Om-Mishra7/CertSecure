from app import app
from app.config import APP_CONFIG
import os
from dotenv import load_dotenv


load_dotenv()  # Loads environment variables from .env file

APP_CONFIG = APP_CONFIG("CertSecure", "0.0.1", os.environ.get("APP_MODE")).config()


if __name__ == "__main__":
    app.run(host=APP_CONFIG["HOST"], port=APP_CONFIG["PORT"], debug=APP_CONFIG["DEBUG"])
