# Author: Om Mishra (om-mishra@projectrexa.dedyn.io)
# Last Modified: 2/12/2023 by Om Mishra

import os
from dotenv import load_dotenv

load_dotenv()  # Loads environment variables from .env file


class APP_CONFIG:
    def __init__(self, app_name, app_version, app_mode):
        self.APP_NAME = app_name
        self.APP_VERSION = app_version
        self.APP_MODE = app_mode
        if os.environ.get("SECRET_KEY") is None:
            raise ValueError("Secret key was not found in environment variables")
        else:
            self.SECRET_KEY = os.environ.get("SECRET_KEY")

    def config(self):
        if self.APP_MODE == "development":
            return self.development_config()
        elif self.APP_MODE == "production":
            return self.production_config()
        elif self.APP_MODE == "testing":
            return self.testing_config()
        else:
            raise ValueError("Invalid app mode")

    def development_config(self):
        return {
            "APP_NAME": self.APP_NAME,
            "APP_VERSION": self.APP_VERSION,
            "APP_MODE": self.APP_MODE,
            "DEBUG": True,
            "HOST": "0.0.0.0",
            "PORT": 80,
            "MONGODB_SETTINGS": {
                "DATABASE": os.environ.get("MONGODB_DATABASE"),
                "HOST": os.environ.get("MONGODB_HOST"),
            },
            "REDIS_SETTINGS": {
                "HOST": os.environ.get("REDIS_HOST"),
            },
            "RECAPTCHA_SETTINGS": {
                "RECAPTCHA_PUBLIC_KEY": os.environ.get("RECAPTCHA_PUBLIC_KEY"),
                "RECAPTCHA_PRIVATE_KEY": os.environ.get("RECAPTCHA_PRIVATE_KEY"),
            },
            "SENDINBLUE_API_KEY": os.environ.get("SENDINBLUE_API_KEY"),
        }

    def production_config(self):
        return {
            "APP_NAME": self.APP_NAME,
            "APP_VERSION": self.APP_VERSION,
            "APP_MODE": self.APP_MODE,
            "DEBUG": False,
            "HOST": "0.0.0.0",
            "PORT": 80,
            "MONGODB_SETTINGS": {
                "DATABASE": os.environ.get("MONGODB_DATABASE"),
                "HOST": os.environ.get("MONGODB_HOST"),
            },
            "REDIS_SETTINGS": {
                "HOST": os.environ.get("REDIS_HOST"),
            },
            "RECAPTCHA_SETTINGS": {
                "RECAPTCHA_PUBLIC_KEY": os.environ.get("RECAPTCHA_PUBLIC_KEY"),
                "RECAPTCHA_PRIVATE_KEY": os.environ.get("RECAPTCHA_PRIVATE_KEY"),
            },
            "SENDINBLUE_API_KEY": os.environ.get("SENDINBLUE_API_KEY"),
        }

    def testing_config(self):
        return {
            "APP_NAME": self.APP_NAME,
            "APP_VERSION": self.APP_VERSION,
            "APP_MODE": self.APP_MODE,
            "DEBUG": True,
            "HOST": "0.0.0.0",
            "PORT": 80,
            "MONGODB_SETTINGS": {
                "DATABASE": os.environ.get("MONGODB_DATABASE"),
                "HOST": os.environ.get("MONGODB_HOST"),
            },
            "REDIS_SETTINGS": {
                "HOST": os.environ.get("REDIS_HOST"),
            },
            "RECAPTCHA_SETTINGS": {
                "RECAPTCHA_PUBLIC_KEY": os.environ.get("RECAPTCHA_PUBLIC_KEY"),
                "RECAPTCHA_PRIVATE_KEY": os.environ.get("RECAPTCHA_PRIVATE_KEY"),
            },
            "SENDINBLUE_API_KEY": os.environ.get("SENDINBLUE_API_KEY"),
        }
