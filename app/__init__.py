import os
import secrets
import requests
import datetime
import hashlib
from functools import wraps
from dotenv import load_dotenv
from app.config import APP_CONFIG
from app.database import connect_monogodb, connect_redis
from app.utils import verify_recaptcha, hash_password, verify_password, send_email
from flask import (
    Flask,
    jsonify,
    request,
    render_template,
    redirect,
    url_for,
    session,
    abort,
    render_template_string,
)
from flask_session import Session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import dns.resolver
import bson
from cryptography.fernet import Fernet
import json
from bson import ObjectId
from web3 import Web3
from pymongo import MongoClient
import os
from datetime import datetime, timedelta


w3 = Web3(
    Web3.HTTPProvider(
        "https://polygon-mumbai.g.alchemy.com/v2/mdeLrZjWjJRKM0wbyWNQmAesbyH0KyMC"
    )
)

contract_address = "0xF0484f969EBAe07814F362E76Dea7e62c28A9D3c"  # Can be generated using the deploy script

with open("app/certsecure-contract.abi") as f:
    contract_abi = f.read()

private_key = "1c660c0bd280f4d96f0783d312d8a2eda5e42c00a246feb6e5c62f03ce984b6a"

public_key = "0xD8842AA0E4b20BfeA273406A249880Dc590Fd027"

certsecure_contract = w3.eth.contract(address=contract_address, abi=contract_abi)


load_dotenv()  # Loads environment variables from .env file

APP_CONFIG = APP_CONFIG("CertSecure", "0.0.1", os.environ.get("APP_MODE")).config()

MONGODB_DATABASE = connect_monogodb(
    APP_CONFIG["MONGODB_SETTINGS"]["HOST"], APP_CONFIG["MONGODB_SETTINGS"]["DATABASE"]
)

REDIS_DATABASE = connect_redis(APP_CONFIG["REDIS_SETTINGS"]["HOST"])

app = Flask(__name__)

# Session configuration


def create_session(app):
    app.config["SESSION_TYPE"] = "redis"
    app.config["SESSION_REDIS"] = REDIS_DATABASE
    app.config["SESSION_COOKIE_SECURE"] = True
    app.config["SESSION_PERMANENT"] = True
    app.config["SESSION_KEY_PREFIX"] = "certsecure"
    app.config["SESSION_COOKIE_NAME"] = "certsecure-session"
    app.config["PERMANENT_SESSION_LIFETIME"] = 86400
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    Session(app)


create_session(app)

# Rate limiting configuration

pool = REDIS_DATABASE.connection_pool
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["3600 per hour"],
    headers_enabled=True,
    strategy="fixed-window",
    storage_uri="redis://",
    storage_options={"connection_pool": pool},
)


# Jinja decorators


@app.template_filter("render")
def render(html_string):
    return render_template(str(html_string))


# Application context processors


@app.context_processor
def recaptcha_site_key():
    return dict(
        RECAPTCHA_SITE_KEY=APP_CONFIG["RECAPTCHA_SETTINGS"]["RECAPTCHA_PUBLIC_KEY"]
    )


@app.context_processor
def app_mode():
    return dict(APP_MODE=APP_CONFIG["APP_MODE"])


# Application route decorators

USER_ROLE = ["user"]
ORGANIZATION_ROLE = ["organization"]
SUPERUSER_ROLE = ["superuser"]


def role_protected_route(allowed_roles):
    def decorator(decorated_function):
        @wraps(decorated_function)
        def wrapper(*args, **kwargs):
            if session.get("loggedIn") is None:
                return redirect(url_for("login"))
            else:
                user_role = session.get("userRole")
                if user_role not in allowed_roles:
                    abort(403)
            return decorated_function(*args, **kwargs)

        return wrapper

    return decorator


# Defining role-specific decorators using the generalized decorator
user_protected_route = role_protected_route(USER_ROLE)
organization_protected_route = role_protected_route(ORGANIZATION_ROLE)
superuser_protected_route = role_protected_route(SUPERUSER_ROLE)


# Application routes


@app.route("/")
@limiter.exempt
def home():
    if session.get("loggedIn") is not None:
        if session.get("userRole") == "user":
            return redirect(url_for("user_dashboard"))
        elif session.get("userRole") == "organization":
            return redirect(url_for("organization_dashboard"))
        elif session.get("userRole") == "superuser":
            return redirect(url_for("superuser_dashboard"))
    return redirect(url_for("home_page"))


@app.route("/home", methods=["GET"])
@limiter.exempt
def home_page():
    return render_template("frontend/home.html"), 200


@app.route("/sign-in", methods=["GET"])
@limiter.exempt
def sign_in():
    if session.get("loggedIn") is not None:
        if session.get("userRole") == "user":
            return redirect(url_for("user_dashboard"))
        elif session.get("userRole") == "organization":
            return redirect(url_for("organization_dashboard"))
        elif session.get("userRole") == "superuser":
            return redirect(url_for("superuser_dashboard"))
    return render_template("frontend/sign-in.html"), 200


@app.route("/api/v1/sign-in", methods=["POST"])
@limiter.limit("30 per minute")
def api_sign_in():
    request_data = request.get_json()
    if (
        (request_data.get("email") is None)
        or (request_data.get("password") is None)
        or (request_data.get("token") is None)
    ):
        return (
            jsonify(
                {
                    "message": "Please provide all the required fields to sign in",
                    "status": "error",
                }
            ),
            400,
        )

    if request_data.get("email").lower().strip().count("@") != 1:
        return (
            jsonify(
                {
                    "message": "Please provide a valid email address",
                    "status": "error",
                }
            ),
            400,
        )

    if not verify_recaptcha(
        APP_CONFIG["RECAPTCHA_SETTINGS"]["RECAPTCHA_PRIVATE_KEY"],
        request_data.get("token"),
    ):
        return (
            jsonify(
                {
                    "message": "Unable to verify reCAPTCHA, please try again",
                    "status": "error",
                }
            ),
            400,
        )

    user = MONGODB_DATABASE.USERS.find_one({"email": request_data.get("email").lower()})

    organization = MONGODB_DATABASE.ORGANIZATIONS.find_one(
        {"email": request_data.get("email").lower()}
    )

    if user is None and organization is None:
        return (
            jsonify(
                {
                    "message": "No user or organization with this email exists",
                    "status": "error",
                }
            ),
            400,
        )

    if user is not None:
        if user.get("is_blocked"):
            return (
                jsonify(
                    {
                        "message": "This account has been blocked, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        if user.get("is_deleted"):
            return (
                jsonify(
                    {
                        "message": "This account has been deleted, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        if user.get("failed_login_attempts") >= 20:
            if user.get("lockout_until") > datetime.utcnow():
                return (
                    jsonify(
                        {
                            "message": "This account has been locked out due to multiple failed login attempts, please try again later",
                            "status": "error",
                        }
                    ),
                    400,
                )
            else:
                MONGODB_DATABASE.USERS.update_one(
                    {"email": request_data.get("email").lower()},
                    {
                        "$set": {
                            "failed_login_attempts": 0,
                            "lockout_until": None,
                        }
                    },
                )

        if not verify_password(request_data.get("password"), user.get("password")):
            MONGODB_DATABASE.USERS.update_one(
                {"email": request_data.get("email").lower()},
                {
                    "$set": {
                        "failed_login_attempts": user.get("failed_login_attempts") + 1,
                        "lockout_until": datetime.utcnow() + timedelta(minutes=5),
                    }
                },
            )
            return (
                jsonify(
                    {
                        "message": "The password you entered is incorrect, please try again",
                        "status": "error",
                    }
                ),
                400,
            )

        if not user.get("email_verified"):
            session.clear()
            session["temploggedIn"] = True
            session["userEmail"] = user.get("email")
            session["userRole"] = user.get("role")
            session["tempLoggedInReason"] = "email_not_verified"
            return (
                jsonify(
                    {
                        "message": "This email address has not been verified, please check your inbox for the verification email or request a new verification email by <a onclick='resendVerificationEmail()' href='#'>clicking here</a>",
                        "status": "error",
                    }
                ),
                400,
            )

        if user.get("two_factor_authentication_enabled"):
            session.clear()
            session["temploggedIn"] = True
            session["userEmail"] = user.get("email")
            session["userRole"] = user.get("role")
            session["tempLoggedInReason"] = "two_factor_authentication_enabled"
            return (
                jsonify(
                    {
                        "message": "Two factor authentication is enabled for this account, please enter the code from your authenticator app to continue",
                        "status": "success",
                    }
                ),
                200,
            )

        session["loggedIn"] = True
        session["userID"] = str(user.get(("_id")))
        session["userRole"] = user.get("role")
        session["userEmail"] = user.get("email")
        session["userTwoFactorAuthenticationEnabled"] = user.get(
            "two_factor_authentication_enabled"
        )

        MONGODB_DATABASE.USERS.update_one(
            {"email": request_data.get("email").lower()},
            {"$set": {"last_login_at": datetime.utcnow()}},
        )

        return (
            jsonify(
                {
                    "message": "The sign in was successful, redirecting you to your dashboard",
                    "status": "success",
                }
            ),
            200,
        )

    if organization is not None:
        if organization.get("is_blocked"):
            return (
                jsonify(
                    {
                        "message": "This account has been blocked, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        if organization.get("is_deleted"):
            return (
                jsonify(
                    {
                        "message": "This account has been deleted, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        if organization.get("failed_login_attempts") >= 5:
            if organization.get("lockout_until") > datetime.utcnow():
                return (
                    jsonify(
                        {
                            "message": "This account has been locked out due to multiple failed login attempts, please try again later",
                            "status": "error",
                        }
                    ),
                    400,
                )
            else:
                MONGODB_DATABASE.ORGANIZATIONS.update_one(
                    {"email": request_data.get("email").lower()},
                    {
                        "$set": {
                            "failed_login_attempts": 0,
                            "lockout_until": None,
                        }
                    },
                )

        if not verify_password(
            request_data.get("password"), organization.get("password")
        ):
            MONGODB_DATABASE.ORGANIZATIONS.update_one(
                {"email": request_data.get("email").lower()},
                {
                    "$set": {
                        "failed_login_attempts": organization.get(
                            "failed_login_attempts"
                        )
                        + 1,
                        "lockout_until": datetime.utcnow() + timedelta(minutes=10),
                    }
                },
            )
            return (
                jsonify(
                    {
                        "message": "The password you entered is incorrect, please try again",
                        "status": "error",
                    }
                ),
                400,
            )

        if not organization.get("email_verified"):
            session.clear()
            session["temploggedIn"] = True
            session["organizationEmail"] = organization.get("email")
            session["organizationRole"] = organization.get("role")
            session["tempLoggedInReason"] = "email_not_verified"

            return (
                jsonify(
                    {
                        "message": "This email address has not been verified, please check your inbox for the verification email or request a new verification email by <a onclick='resendVerificationEmail()' href='#'>clicking here</a>",
                        "status": "error",
                    }
                ),
                400,
            )

        if not organization.get("domain_address_verified"):
            session.clear()
            session["sign_up_stage"] = "organization_domain_verification"
            session["organization_email"] = organization.get("email").lower()
            session["organization_name"] = organization.get("name")
            session["organization_domain_address"] = organization.get("domain_address")

            return (
                jsonify(
                    {
                        "message": "The domain for this organization has not been verified, click <a href='/organization/domain-verification'>here</a> to verify the domain",
                        "status": "error",
                    },
                )
            ), 403

        try:
            domain_txt_record = (
                dns.resolver.resolve(
                    (
                        "certsecure-domain-verification."
                        + organization.get("domain_address")
                    ),
                    "TXT",
                )[0]
                .strings[0]
                .decode("utf-8")
                .lower()
                .replace('"', "")
                .replace(" ", "")
                .strip()
            )
        except Exception as e:
            MONGODB_DATABASE.ORGANIZATIONS.update_one(
                {"email": organization.get("email").lower()},
                {
                    "$set": {
                        "domain_address_verified": False,
                    }
                },
            )
            session.clear()
            session["sign_up_stage"] = "organization_domain_verification"
            session["organization_email"] = organization.get("email").lower()
            session["organization_name"] = organization.get("name")
            session["organization_domain_address"] = organization.get("domain_address")
            return (
                jsonify(
                    {
                        "message": "Unable to find the TXT record for the domain, you can click <a href='/organization/domain-verification'>here</a> to verify the domain again",
                        "status": "error",
                    }
                ),
                400,
            )

        if (
            domain_txt_record
            != organization.get("domain_address_verification_token").lower()
        ):
            MONGODB_DATABASE.ORGANIZATIONS.update_one(
                {"email": request_data.get("email").lower()},
                {
                    "$set": {
                        "domain_address_verified": False,
                    }
                },
            )
            session.clear()
            session["sign_up_stage"] = "organization_domain_verification"
            session["organization_email"] = organization.get("email").lower()
            session["organization_name"] = organization.get("name")
            session["organization_domain_address"] = organization.get("domain_address")
            return (
                jsonify(
                    {
                        "message": "The domain verification token does not match, you can click <a href='/organization/domain-verification'>here</a> to verify the domain again",
                        "status": "error",
                    }
                ),
                400,
            )

        if organization.get("two_factor_authentication_enabled"):
            session.clear()
            session["temploggedIn"] = True
            session["organizationEmail"] = organization.get("email")
            session["organizationRole"] = organization.get("role")
            session["tempLoggedInReason"] = "two_factor_authentication_enabled"
            return (
                jsonify(
                    {
                        "message": "Two factor authentication is enabled for this account, please enter the code from your authenticator app to continue",
                        "status": "success",
                    }
                ),
                200,
            )

        session["loggedIn"] = True
        session["userID"] = str(organization.get("_id"))
        session["userRole"] = organization.get("role")
        session["organizationName"] = organization.get("name")
        session["organizationEmail"] = organization.get("email")
        session["organizationDomainAddress"] = organization.get("domain_address")
        session["organizationPhoneNumer"] = organization.get("phone")
        session["organizationTwoFactorAuthenticationEnabled"] = organization.get(
            "two_factor_authentication_enabled"
        )

        MONGODB_DATABASE.ORGANIZATIONS.update_one(
            {"email": request_data.get("email").lower()},
            {"$set": {"last_login_at": datetime.utcnow()}},
        )

        return (
            jsonify(
                {
                    "message": "The sign in was successful, redirecting you to your organization's dashboard",
                    "status": "success",
                }
            ),
            200,
        )


# User sign out route


@app.route("/sign-out", methods=["GET"])
@limiter.exempt
def sign_out():
    session.clear()
    return redirect(url_for("sign_in"))


# User registration routes


@app.route("/sign-up", methods=["GET"])
@limiter.exempt
def sign_up():
    if session.get("loggedIn") is not None:
        if session.get("userRole") == "user":
            return redirect(url_for("user_dashboard"))
        elif session.get("userRole") == "organization":
            return redirect(url_for("organization_dashboard"))
        elif session.get("userRole") == "superuser":
            return redirect(url_for("superuser_dashboard"))
    if session.get("temploggedIn") is not None:
        return redirect(url_for("verification_email"))
    return render_template("frontend/sign-up.html"), 200


@app.route("/user/sign-up", methods=["GET"])
@limiter.exempt
def user_sign_up():
    # Implement registration page
    return render_template("frontend/user-sign-up.html"), 200


@app.route("/api/v1/user/sign-up", methods=["POST"])
@limiter.limit("30 per minute")
def api_user_sign_up():
    request_data = request.get_json()
    if (
        (request_data.get("email") is None)
        or (request_data.get("password") is None)
        or (request_data.get("token") is None)
    ):
        return (
            jsonify(
                {
                    "message": "Please provide all the required fields to register",
                    "status": "error",
                }
            ),
            400,
        )

    if request_data.get("email").lower().strip().count("@") != 1:
        return (
            jsonify(
                {
                    "message": "Please provide a valid email address",
                    "status": "error",
                }
            ),
            400,
        )

    if not verify_recaptcha(
        APP_CONFIG["RECAPTCHA_SETTINGS"]["RECAPTCHA_PRIVATE_KEY"],
        request_data.get("token"),
    ):
        return (
            jsonify(
                {
                    "message": "Unable to verify reCAPTCHA, please try again",
                    "status": "error",
                }
            ),
            400,
        )

    if (
        MONGODB_DATABASE.USERS.find_one({"email": request_data.get("email").lower()})
        is not None
    ):
        return (
            jsonify(
                {
                    "message": "User with this email already exists, please <a href='/sign-in'>sign in</a> instead",
                    "status": "error",
                }
            ),
            400,
        )

    try:
        if (
            requests.get(
                f'https://api.pwnedpasswords.com/range/{hashlib.sha1(request_data.get("password").encode("utf-8")).hexdigest()[:5]}',
                timeout=2,
            ).text.count(
                hashlib.sha1(request_data.get("password").encode("utf-8"))
                .hexdigest()[5:]
                .upper()
            )
            > 0
        ):
            return (
                jsonify(
                    {
                        "message": "This password has been compromised in a data breach, please use a different password",
                        "status": "error",
                    },
                ),
                400,
            )
    except requests.exceptions.RequestException as e:
        print(e)
        pass

    MONGODB_DATABASE.USERS.insert_one(
        {
            "email": request_data.get("email").lower(),
            "password": hash_password(request_data.get("password")),
            "failed_login_attempts": 0,
            "lockout_until": None,
            "role": "user",
            "email_verified": False,
            "two_factor_authentication_enabled": False,
            "account_created_at": datetime.utcnow(),
            "last_login_at": datetime.utcnow(),
            "is_active": True,
            "is_deleted": False,
            "is_blocked": False,
        }
    )

    EMAIL_VERIFICATION_TOKEN = secrets.token_urlsafe(32)

    MONGODB_DATABASE.TOKENS.delete_many(
        {"email": request_data.get("email").lower(), "token_type": "email_verification"}
    )

    MONGODB_DATABASE.TOKENS.insert_one(
        {
            "email": request_data.get("email").lower(),
            "token_for": "user",
            "token": EMAIL_VERIFICATION_TOKEN,
            "token_type": "email_verification",
            "token_expires_at": datetime.utcnow() + timedelta(hours=2),
            "token_used": False,
        }
    )

    if send_email(
        APP_CONFIG["SENDINBLUE_API_KEY"],
        request_data.get("email"),
        "user-registration",
        EMAIL_VERIFICATION_TOKEN,
    ):
        return (
            jsonify(
                {
                    "message": "The registration was successful, please check your inbox for the next steps",
                    "status": "success",
                },
            )
        ), 200

    else:
        return (
            jsonify(
                {
                    "message": "The registration was successful, but we were unable to send you an email, please try again later",
                    "status": "success",
                },
            )
        ), 200


# Organization registration routes


@app.route("/organization/sign-up", methods=["GET"])
@limiter.exempt
def organization_sign_up():
    if session.get("loggedIn") is not None:
        if session.get("userRole") == "user":
            return redirect(url_for("user_dashboard"))
        elif session.get("userRole") == "organization":
            return redirect(url_for("organization_dashboard"))
        elif session.get("userRole") == "superuser":
            return redirect(url_for("superuser_dashboard"))
    if session.get("temploggedIn") is not None:
        return redirect(url_for("organization_domain_verification"))
    return render_template("frontend/organization-sign-up.html"), 200


@app.route("/api/v1/organization/sign-up", methods=["POST"])
@limiter.limit("30 per minute")
def api_organization_sign_up():
    request_data = request.get_json()
    if (
        request_data.get("organization_name") is None
        or request_data.get("organization_domain_address") is None
        or request_data.get("organization_email") is None
        or request_data.get("organization_phone") is None
        or request_data.get("organization_password") is None
        or request_data.get("organization_confirm_password") is None
        or request_data.get("organization_industry") is None
        or request_data.get("organization_size") is None
        or request_data.get("organization_country") is None
        or request_data.get("recaptcha_token") is None
    ):
        return (
            jsonify(
                {
                    "message": "Please provide all the required fields to register",
                    "status": "error",
                }
            ),
            400,
        )

    if request_data.get("organization_email").lower().strip().count("@") != 1:
        return (
            jsonify(
                {
                    "message": "Please provide a valid email address",
                    "status": "error",
                }
            ),
            400,
        )

    if not verify_recaptcha(
        APP_CONFIG["RECAPTCHA_SETTINGS"]["RECAPTCHA_PRIVATE_KEY"],
        request_data.get("recaptcha_token"),
    ):
        return (
            jsonify(
                {
                    "message": "Unable to verify reCAPTCHA, please try again",
                    "status": "error",
                }
            ),
            400,
        )

    if request_data.get("organization_password") != request_data.get(
        "organization_confirm_password"
    ):
        return (
            jsonify(
                {
                    "message": "Passwords do not match, please try again",
                    "status": "error",
                }
            ),
            400,
        )

    try:
        if (
            requests.get(
                f'https://api.pwnedpasswords.com/range/{hashlib.sha1(request_data.get("organization_password").encode("utf-8")).hexdigest()[:5]}',
                timeout=2,
            ).text.count(
                hashlib.sha1(request_data.get("organization_password").encode("utf-8"))
                .hexdigest()[5:]
                .upper()
            )
            > 0
        ):
            return (
                jsonify(
                    {
                        "message": "This password has been compromised in a data breach, please use a different password",
                        "status": "error",
                    },
                ),
                400,
            )
    except requests.exceptions.RequestException as e:
        print(e)
        pass

    if (
        MONGODB_DATABASE.USERS.find_one(
            {"email": request_data.get("organization_email").lower()}
        )
        is not None
    ):
        return (
            jsonify(
                {
                    "message": "User with this email already exists, please <a href='/sign-in'>sign in</a> instead",
                    "status": "error",
                }
            ),
            400,
        )

    if (
        MONGODB_DATABASE.ORGANIZATIONS.find_one(
            {"email": request_data.get("organization_email").lower()}
        )
        is not None
    ):
        return (
            jsonify(
                {
                    "message": "Organization with this email already exists, please <a href='/sign-in'>sign in</a> instead",
                    "status": "error",
                }
            ),
            400,
        )

    if (
        MONGODB_DATABASE.ORGANIZATIONS.find_one(
            {"domain_address": request_data.get("organization_domain_address").lower()}
        )
        is not None
    ):
        return (
            jsonify(
                {
                    "message": "Organization with this domain address already exists, please <a href='/sign-in'>sign in</a> instead",
                    "status": "error",
                }
            ),
            400,
        )

    MONGODB_DATABASE.ORGANIZATIONS.insert_one(
        {
            "name": request_data.get("organization_name"),
            "domain_address": request_data.get("organization_domain_address")
            .lower()
            .strip(),
            "domain_address_verified": False,
            "domain_address_verification_token": secrets.token_urlsafe(64).lower(),
            "email": request_data.get("organization_email").lower().strip(),
            "email_verified": False,
            "phone": request_data.get("organization_phone"),
            "password": hash_password(request_data.get("organization_password")),
            "failed_login_attempts": 0,
            "lockout_until": None,
            "role": "organization",
            "two_factor_authentication_enabled": False,
            "industry": request_data.get("organization_industry"),
            "size": request_data.get("organization_size"),
            "country": request_data.get("organization_country"),
            "account_created_at": datetime.utcnow(),
            "last_login_at": datetime.utcnow(),
            "is_active": True,
            "is_deleted": False,
            "is_blocked": False,
        }
    )

    EMAIL_VERIFICATION_TOKEN = secrets.token_urlsafe(32)

    MONGODB_DATABASE.TOKENS.delete_many(
        {
            "email": request_data.get("organization_email").lower(),
            "token_type": "email_verification",
        }
    )

    MONGODB_DATABASE.TOKENS.insert_one(
        {
            "email": request_data.get("organization_email").lower(),
            "token_for": "organization",
            "token": EMAIL_VERIFICATION_TOKEN,
            "token_type": "email_verification",
            "token_expires_at": datetime.utcnow() + timedelta(hours=2),
            "token_used": False,
        }
    )

    if send_email(
        APP_CONFIG["SENDINBLUE_API_KEY"],
        request_data.get("organization_email").lower().strip(),
        "organization-registration",
        EMAIL_VERIFICATION_TOKEN,
    ):
        session["sign_up_stage"] = "organization_domain_verification"
        session["organization_email"] = request_data.get("organization_email").lower()
        session["organization_name"] = request_data.get("organization_name")
        session["organization_domain_address"] = request_data.get(
            "organization_domain_address"
        )

        return (
            jsonify(
                {
                    "message": "The registration was successful, please check your inbox for the next steps",
                    "status": "success",
                },
            )
        ), 200

    else:
        return (
            jsonify(
                {
                    "message": "The registration was successful, but we were unable to send you an email, please try again later",
                    "status": "success",
                },
            )
        ), 200


# Organization domain verification routes


@app.route("/organization/domain-verification", methods=["GET"])
@limiter.exempt
def organization_domain_verification():
    if session.get("sign_up_stage") != "organization_domain_verification":
        return redirect(url_for("organization_sign_up"))
    domain_verification_token = MONGODB_DATABASE.ORGANIZATIONS.find_one(
        {"email": session.get("organization_email")}
    ).get("domain_address_verification_token")
    return (
        render_template(
            "frontend/organization-domain-verification.html",
            domain_verification_token=domain_verification_token,
        ),
        200,
    )


@app.route("/api/v1/organization/domain-verification", methods=["POST"])
@limiter.limit("30 per minute")
def api_organization_domain_verification():
    request_data = request.get_json()
    if request_data.get("token") is None:
        return (
            jsonify(
                {
                    "message": "reCAPTCHA token is missing, reload the page and try again",
                    "status": "error",
                }
            ),
            400,
        )

    if session.get("sign_up_stage") != "organization_domain_verification":
        session.clear()
        return (
            jsonify(
                {
                    "message": "Invalid application state, please reload the page and try again",
                    "status": "error",
                }
            ),
            400,
        )

    if not verify_recaptcha(
        APP_CONFIG["RECAPTCHA_SETTINGS"]["RECAPTCHA_PRIVATE_KEY"],
        request_data.get("token"),
    ):
        return (
            jsonify(
                {
                    "message": "Unable to verify reCAPTCHA, please try again",
                    "status": "error",
                }
            ),
            400,
        )

    domain_verification_token = MONGODB_DATABASE.ORGANIZATIONS.find_one(
        {"email": session.get("organization_email")}
    ).get("domain_address_verification_token")

    try:
        domain_txt_record = (
            dns.resolver.resolve(
                (
                    "certsecure-domain-verification."
                    + session.get("organization_domain_address")
                ),
                "TXT",
            )[0]
            .strings[0]
            .decode("utf-8")
            .lower()
            .replace('"', "")
            .replace(" ", "")
            .strip()
        )
    except Exception as e:
        print(e)
        return (
            jsonify(
                {
                    "message": "Unable to find the TXT record for the domain, please try again",
                    "status": "error",
                }
            ),
            400,
        )

    if domain_verification_token.lower() != domain_txt_record:
        return (
            jsonify(
                {
                    "message": "The domain verification token does not match, please try again",
                    "status": "error",
                }
            ),
            400,
        )

    MONGODB_DATABASE.ORGANIZATIONS.update_one(
        {"email": session.get("organization_email")},
        {"$set": {"domain_address_verified": True}},
    )

    session.clear()

    return (
        jsonify(
            {
                "message": "The domain verification was successful, you can now <a href='/sign-in'>sign in</a> to continue",
                "status": "success",
            }
        ),
        200,
    )


# Organization Routes


@app.route("/organization/issue/certificate", methods=["GET"])
@organization_protected_route
@limiter.exempt
def organization_issue_certificate():
    return redirect(url_for("create_certificate_batch"))


@app.route("/organization/select/certificate-template", methods=["GET"])
@organization_protected_route
@limiter.exempt
def create_certificate_batch():
    CERTIFICATE_TEMPLATES = MONGODB_DATABASE.CERTIFICATE_TEMPLATES.find()
    return (
        render_template(
            "frontend/create-certificate-batch.html",
            CERTIFICATE_TEMPLATES=CERTIFICATE_TEMPLATES,
        ),
        200,
    )


@app.route("/organization/create/certificate", methods=["GET"])
@organization_protected_route
@limiter.exempt
def api_create_certificate():
    if request.args.get("certificateID") is None:
        return (
            jsonify(
                {
                    "message": "Please provide all the required fields to create a certificate",
                    "status": "error",
                }
            ),
            400,
        )

    template_details = MONGODB_DATABASE.CERTIFICATE_TEMPLATES.find_one(
        {"_id": bson.ObjectId(request.args.get("certificateID"))}
    )

    return (
        render_template(
            "frontend/create-certificate.html",
            templateID=request.args.get("certificateID"),
            template_details=template_details,
        ),
        200,
    )


# Utility routes


@app.route("/api/v1/organization/create-certificates", methods=["POST"])
@organization_protected_route
@limiter.limit("30 per minute")
def api_create_certificates():
    if request.files.get("csv-file") is None:
        return (
            jsonify(
                {
                    "message": "Please provide a CSV file to convert",
                    "status": "error",
                }
            ),
            400,
        )

    if request.files.get("csv-file").filename.split(".")[-1] != "csv":
        return (
            jsonify(
                {
                    "message": "Please provide a CSV file to convert",
                    "status": "error",
                }
            ),
            400,
        )

    try:
        csv_dict = {}

        csv_file = request.files.get("csv-file").read().decode("utf-8").split("\n")
        csv_file = [i.strip() for i in csv_file]
        csv_file = [i.replace("\r", "") for i in csv_file]

        csv_dict["columns"] = csv_file[0].split(",")

        csv_dict["data"] = []

        for i in csv_file[1:]:
            if len(i) > 0:
                csv_dict["data"].append(i.split(","))

        certificate_details = MONGODB_DATABASE.CERTIFICATE_TEMPLATES.find_one(
            {"_id": bson.ObjectId(request.form.get("certificateID"))}
        )

        required_fields = []

        for field_detail in certificate_details.get("certificate_fields"):
            required_fields.append(
                certificate_details.get("certificate_fields")[field_detail]["name"]
            )

        if certificate_details is None:
            return (
                jsonify(
                    {
                        "message": "Invalid certificate ID, please check the link and try again",
                        "status": "error",
                    }
                ),
                400,
            )

        for field_detail in certificate_details.get("certificate_fields"):
            if (
                certificate_details.get("certificate_fields")[field_detail]["name"]
            ) not in csv_dict.get("columns"):
                return (
                    jsonify(
                        {
                            "message": f"The CSV file does not contain the required field {certificate_details.get('certificate_fields')[field_detail]['name']}, please check the file and try again",
                            "status": "error",
                        }
                    ),
                    400,
                )

        if len(csv_dict.get("data")) > 1000:
            return (
                jsonify(
                    {
                        "message": "The CSV file contains more than 1000 rows, please reduce the number of rows and try again",
                        "status": "error",
                    }
                ),
                400,
            )

        if len(csv_dict.get("data")) == 0:
            return (
                jsonify(
                    {
                        "message": "The CSV file does not contain any data, please check the file and try again",
                        "status": "error",
                    }
                ),
                400,
            )

        for i in csv_dict.get("data"):
            certificate_metadata = {}
            certificate_data = {}
            if certificate_details.get("certificate_type") == "marksheet":
                for l in range(0, len(csv_dict.get("columns"))):
                    if csv_dict.get("columns")[l] not in required_fields:
                        certificate_data[csv_dict.get("columns")[l]] = i[l]
            for j in range(len(certificate_details.get("certificate_fields"))):
                for k in certificate_details.get("certificate_fields"):
                    if (
                        certificate_details.get("certificate_fields")[k]["name"]
                        == csv_dict.get("columns")[j]
                    ):
                        certificate_data[
                            certificate_details.get("certificate_fields")[k]["id"]
                        ] = i[j].strip()

            certificate_metadata["certificate_template_id"] = certificate_details.get(
                "_id"
            )
            certificate_metadata["certificate_name"] = certificate_details[
                "certificate_name"
            ]
            certificate_metadata["certificate_publsihing_status"] = "pending"
            certificate_metadata["certificate_publishing_attempts"] = 0
            certificate_metadata["certificate_published_at"] = datetime.utcnow()
            certificate_metadata["certificate_published_by_organization"] = session.get(
                "organizationName"
            )
            certificate_metadata[
                "certificate_published_by_organization_id"
            ] = session.get("userID")
            certificate_metadata["certificate_published_to_name"] = certificate_data[
                "recipient_name"
            ].strip()
            certificate_metadata["certificate_published_to_email"] = (
                certificate_data["recipient_email_id"].lower().strip()
            )

            certificate_metadata["certificate_data"] = certificate_data

            if (
                MONGODB_DATABASE.CERTIFICATES.find_one(
                    {
                        "certificate_data": certificate_data,
                        "certificate_template_id": certificate_details.get("_id"),
                        "certificate_published_to_email": certificate_data.get(
                            "recipient_email_id"
                        ),
                    }
                )
                is not None
            ):
                return (
                    jsonify(
                        {
                            "message": f"Certificate for {certificate_data.get('recipient_email_id')} already exists, please check the CSV file and try again",
                            "status": "error",
                        }
                    ),
                    400,
                )

            inserted_record = MONGODB_DATABASE.CERTIFICATES.insert_one(
                certificate_metadata
            )

            print(APP_CONFIG["SENDINBLUE_API_KEY"])

            print(send_email(
                APP_CONFIG["SENDINBLUE_API_KEY"],
                certificate_data.get("recipient_email_id"),
                "certificate-issued",
                str(inserted_record.inserted_id).replace('"', "").replace("\n", ""),
            ))   

            response = requests.post(f"https://api-certsecure.om-mishra.com/add-certificate/{str(inserted_record.inserted_id)}")

        return (
            jsonify(
                {
                    "message": f"{len(csv_dict.get('data'))} certificates were created successfully",
                    "status": "success",
                }
            ),
            200,
        )

    except Exception as e:
        print(e)
        return (
            jsonify(
                {
                    "message": "Unable to create certificates, please check the CSV file and try again",
                    "status": "error",
                }
            ),
            400,
        )


@app.route("/api/v1/resend-verification-email", methods=["POST"])
@limiter.limit("10 per day")
def api_verification_email():
    user_type = None

    if session.get("temploggedIn") is None:
        return (
            jsonify(
                {
                    "message": "Invalid application state, please reload the page and try again",
                    "status": "error",
                }
            ),
            400,
        )

    if session.get("tempLoggedInReason") != "email_not_verified":
        return (
            jsonify(
                {
                    "message": "Invalid application state, please reload the page and try again",
                    "status": "error",
                }
            ),
            400,
        )

    request_data = request.get_json()
    if request_data.get("email") is None:
        return (
            jsonify(
                {
                    "message": "Invalid request, please reload the page and try again",
                    "status": "error",
                }
            ),
            400,
        )

    if request_data.get("email").lower().strip().count("@") != 1:
        return (
            jsonify(
                {
                    "message": "Please provide a valid email address",
                    "status": "error",
                }
            ),
            400,
        )

    user = MONGODB_DATABASE.USERS.find_one({"email": request_data.get("email").lower()})

    organization = MONGODB_DATABASE.ORGANIZATIONS.find_one(
        {"email": request_data.get("email").lower()}
    )

    if user is None and organization is None:
        return (
            jsonify(
                {
                    "message": "No user or organization with this email exists",
                    "status": "error",
                }
            ),
            400,
        )

    if user is not None:
        user_tye = "user"

    if organization is not None:
        user_type = "organization"

    EMAIL_VERIFICATION_TOKEN = secrets.token_urlsafe(32)

    MONGODB_DATABASE.TOKENS.delete_many(
        {"email": request_data.get("email").lower(), "token_type": "email_verification"}
    )

    MONGODB_DATABASE.TOKENS.insert_one(
        {
            "email": request_data.get("email").lower(),
            "token_for": user_type,
            "token": EMAIL_VERIFICATION_TOKEN,
            "token_type": "email_verification",
            "token_expires_at": datetime.utcnow() + timedelta(hours=2),
            "token_used": False,
        }
    )

    if send_email(
        APP_CONFIG["SENDINBLUE_API_KEY"],
        request_data.get("email").lower(),
        "email-verification",
        EMAIL_VERIFICATION_TOKEN,
    ):
        return (
            jsonify(
                {
                    "message": "The verification email was sent successfully, please check your inbox for the next steps",
                    "status": "success",
                },
            )
        ), 200

    else:
        return (
            jsonify(
                {
                    "message": "The verification email was not sent successfully, please try again later",
                    "status": "error",
                },
            )
        ), 400


@app.route("/forgot-password", methods=["GET"])
@limiter.exempt
def forgot_password():
    if session.get("loggedIn") is not None:
        if session.get("userRole") == "user":
            return redirect(url_for("user_dashboard"))
        elif session.get("userRole") == "organization":
            return redirect(url_for("organization_dashboard"))
        elif session.get("userRole") == "superuser":
            return redirect(url_for("superuser_dashboard"))
    if session.get("temploggedIn") is not None:
        return redirect(url_for("sign_in"))
    return render_template("frontend/forgot-password.html"), 200


@app.route("/api/v1/forgot-password", methods=["POST"])
@limiter.limit("10 per day")
def api_forgot_password():
    request_data = request.get_json()
    if (request_data.get("email") is None) or (request_data.get("token") is None):
        return (
            jsonify(
                {
                    "message": "Please provide all the required fields to request a password reset",
                    "status": "error",
                }
            ),
            400,
        )

    if request_data.get("email").lower().strip().count("@") != 1:
        return (
            jsonify(
                {
                    "message": "Please provide a valid email address",
                    "status": "error",
                }
            ),
            400,
        )

    if not verify_recaptcha(
        APP_CONFIG["RECAPTCHA_SETTINGS"]["RECAPTCHA_PRIVATE_KEY"],
        request_data.get("token"),
    ):
        return (
            jsonify(
                {
                    "message": "Unable to verify reCAPTCHA, please try again",
                    "status": "error",
                }
            ),
            400,
        )

    user = MONGODB_DATABASE.USERS.find_one({"email": request_data.get("email").lower()})

    organization = MONGODB_DATABASE.ORGANIZATIONS.find_one(
        {"email": request_data.get("email").lower()}
    )

    if user is None and organization is None:
        return (
            jsonify(
                {
                    "message": "No user or organization with this email exists",
                    "status": "error",
                }
            ),
            400,
        )

    if user is not None:
        if user.get("is_blocked"):
            return (
                jsonify(
                    {
                        "message": "This account has been blocked, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        if user.get("is_deleted"):
            return (
                jsonify(
                    {
                        "message": "This account has been deleted, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        PASSWORD_RESET_TOKEN = secrets.token_urlsafe(32)

        MONGODB_DATABASE.TOKENS.delete_many(
            {"email": request_data.get("email").lower(), "token_type": "password_reset"}
        )

        MONGODB_DATABASE.TOKENS.insert_one(
            {
                "email": request_data.get("email").lower(),
                "token_for": "user",
                "token": PASSWORD_RESET_TOKEN,
                "token_type": "password_reset",
                "token_expires_at": datetime.utcnow() + timedelta(hours=2),
                "token_used": False,
            }
        )

        if send_email(
            APP_CONFIG["SENDINBLUE_API_KEY"],
            request_data.get("email").lower(),
            "password-reset",
            PASSWORD_RESET_TOKEN,
        ):
            return (
                jsonify(
                    {
                        "message": "The password reset email was sent successfully, please check your inbox for the next steps",
                        "status": "success",
                    },
                )
            ), 200

        else:
            return (
                jsonify(
                    {
                        "message": "The password reset email was not sent successfully, please try again later",
                        "status": "error",
                    },
                )
            ), 400

    if organization is not None:
        if organization.get("is_blocked"):
            return (
                jsonify(
                    {
                        "message": "This account has been blocked, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        if organization.get("is_deleted"):
            return (
                jsonify(
                    {
                        "message": "This account has been deleted, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        PASSWORD_RESET_TOKEN = secrets.token_urlsafe(32)

        MONGODB_DATABASE.TOKENS.delete_many(
            {"email": request_data.get("email").lower(), "token_type": "password_reset"}
        )

        MONGODB_DATABASE.TOKENS.insert_one(
            {
                "email": request_data.get("email").lower(),
                "token_for": "organization",
                "token": PASSWORD_RESET_TOKEN,
                "token_type": "password_reset",
                "token_expires_at": datetime.utcnow() + timedelta(hours=2),
                "token_used": False,
            }
        )

        if send_email(
            APP_CONFIG["SENDINBLUE_API_KEY"],
            request_data.get("email").lower(),
            "password-reset",
            PASSWORD_RESET_TOKEN,
        ):
            return (
                jsonify(
                    {
                        "message": "The password reset email was sent successfully, please check your inbox for the next steps",
                        "status": "success",
                    },
                )
            ), 200

        else:
            return (
                jsonify(
                    {
                        "message": "The password reset email was not sent successfully, please try again later",
                        "status": "error",
                    },
                )
            ), 400


@app.route("/reset-password", methods=["GET"])
@limiter.exempt
def reset_password():
    if session.get("loggedIn") is not None:
        if session.get("userRole") == "user":
            return redirect(url_for("user_dashboard"))
        elif session.get("userRole") == "organization":
            return redirect(url_for("organization_dashboard"))
        elif session.get("userRole") == "superuser":
            return redirect(url_for("superuser_dashboard"))
    if request.args.get("token") is None:
        return (
            jsonify(
                {
                    "message": "Invalid token, please check your email for the correct link",
                    "status": "error",
                }
            ),
            400,
        )

    return render_template("frontend/reset-password.html"), 200


@app.route("/api/v1/reset-password", methods=["GET"])
@limiter.exempt
def api_reset_password():
    if session.get("loggedIn") is not None:
        if session.get("userRole") == "user":
            return redirect(url_for("user_dashboard"))
        elif session.get("userRole") == "organization":
            return redirect(url_for("organization_dashboard"))
        elif session.get("userRole") == "superuser":
            return redirect(url_for("superuser_dashboard"))
    return render_template("frontend/reset-password.html"), 200


@app.route("/api/v1/reset-password", methods=["POST"])
@limiter.limit("10 per day")
def api_reset_password_post():
    request_data = request.get_json()
    if (
        (request_data.get("token") is None)
        or (request_data.get("password") is None)
        or (request_data.get("reset_token") is None)
    ):
        return (
            jsonify(
                {
                    "message": "The request is missing required fields, please reload the page and try again",
                    "status": "error",
                }
            ),
            400,
        )

    if len(request_data.get("password")) < 8:
        return (
            jsonify(
                {
                    "message": "The password must be at least 8 characters long",
                    "status": "error",
                }
            ),
            400,
        )

    if not verify_recaptcha(
        APP_CONFIG["RECAPTCHA_SETTINGS"]["RECAPTCHA_PRIVATE_KEY"],
        request_data.get("token"),
    ):
        return (
            jsonify(
                {
                    "message": "Unable to verify reCAPTCHA, please try again",
                    "status": "error",
                }
            ),
            400,
        )

    token = MONGODB_DATABASE.TOKENS.find_one(
        {"token": request_data.get("reset_token"), "token_type": "password_reset"}
    )

    if token is None:
        return (
            jsonify(
                {
                    "message": "Invalid token, please check your email for the correct link",
                    "status": "error",
                }
            ),
            400,
        )

    if token.get("token_used"):
        return (
            jsonify(
                {
                    "message": "This token has already been used, please check your email for the correct link",
                    "status": "error",
                },
            ),
            400,
        )

    if token.get("token_expires_at") < datetime.utcnow():
        return (
            jsonify(
                {
                    "message": "This token has expired, please request a new token by <a href='/forgot-password'>clicking here</a>",
                    "status": "error",
                }
            ),
            400,
        )

    if token.get("token_for") == "user":
        user = MONGODB_DATABASE.USERS.find_one({"email": token.get("email")})

        if user is None:
            return (
                jsonify(
                    {
                        "message": "Invalid token, please check your email for the correct link",
                        "status": "error",
                    }
                ),
                400,
            )

        if user.get("is_blocked"):
            return (
                jsonify(
                    {
                        "message": "This account has been blocked, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        if user.get("is_deleted"):
            return (
                jsonify(
                    {
                        "message": "This account has been deleted, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        MONGODB_DATABASE.USERS.update_one(
            {"email": token.get("email")},
            {"$set": {"password": hash_password(request_data.get("password"))}},
        )

    elif token.get("token_for") == "organization":
        organization = MONGODB_DATABASE.ORGANIZATIONS.find_one(
            {"email": token.get("email")}
        )

        if organization is None:
            return (
                jsonify(
                    {
                        "message": "Invalid token, please check your email for the correct link",
                        "status": "error",
                    }
                ),
                400,
            )

        if organization.get("is_blocked"):
            return (
                jsonify(
                    {
                        "message": "This account has been blocked, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        if organization.get("is_deleted"):
            return (
                jsonify(
                    {
                        "message": "This account has been deleted, please contact support for more information",
                        "status": "error",
                    }
                ),
                400,
            )

        MONGODB_DATABASE.ORGANIZATIONS.update_one(
            {"email": token.get("email")},
            {"$set": {"password": hash_password(request_data.get("password"))}},
        )

    else:
        return (
            jsonify(
                {
                    "message": "Invalid token, please check your email for the correct link",
                    "status": "error",
                }
            ),
            400,
        )

    MONGODB_DATABASE.TOKENS.update_one(
        {"token": request_data.get("reset_token")}, {"$set": {"token_used": True}}
    )

    return (
        jsonify(
            {
                "message": "The password was reset successfully, you can now <a href='/sign-in'>sign in</a> to continue",
                "status": "success",
            }
        ),
        200,
    )


@app.route("/certificate/<certificate_id>", methods=["GET"])
@limiter.exempt
def certificate(certificate_id):
    CERTIFICATE = None
    CERTIFICATE = MONGODB_DATABASE.CERTIFICATES.find_one(
        {"_id": bson.ObjectId(certificate_id)}
    )

    if CERTIFICATE is None:
        return (
            jsonify(
                {
                    "message": "Invalid certificate ID, please check the link and try again",
                    "status": "error",
                }
            ),
            400,
        )

    CERTIFICATE_TEMPLATE = MONGODB_DATABASE.CERTIFICATE_TEMPLATES.find_one(
        {"_id": bson.ObjectId(CERTIFICATE["certificate_template_id"])}
    )

    return (
        render_template_string(
            CERTIFICATE_TEMPLATE["certificate_template"], CERTIFICATE=CERTIFICATE
        ),
        200,
    )



# Two factor authentication routes


@app.route("/user/settings/two-factor-authentication", methods=["GET"])
@user_protected_route
@limiter.exempt
def user_two_factor_authentication_settings():
    if session.get("userTwoFactorAuthenticationEnabled"):
        return redirect(url_for("user_dashboard"))
    return render_template("frontend/user-two-factor-authentication-settings.html"), 200


@app.route("/organization/settings/two-factor-authentication", methods=["GET"])
@organization_protected_route
@limiter.exempt
def organization_two_factor_authentication_settings():
    if session.get("organizationTwoFactorAuthenticationEnabled"):
        return redirect(url_for("organization_dashboard"))
    return (
        render_template(
            "frontend/organization-two-factor-authentication-settings.html"
        ),
        200,
    )


@app.route("/api/v1/setup/two-factor-authentication", methods=["POST"])
@limiter.limit("30 per minute")
def api_setup_two_factor_authentication():
    return (
        jsonify(
            {
                "message": "Two factor authentication is not supported yet",
                "status": "error",
            }
        ),
        400,
    )


# Dashboard routes


@app.route("/user/dashboard", methods=["GET"])
@user_protected_route
@limiter.exempt
def user_dashboard():
    USER_CERTIFICATES = MONGODB_DATABASE.CERTIFICATES.find(
        {"certificate_published_to_email": session.get("userEmail")}
    )
    return (
        render_template(
            "frontend/user-dashboard.html", USER_CERTIFICATES=list(USER_CERTIFICATES)
        ),
        200,
    )


@app.route("/organization/dashboard", methods=["GET"])
@organization_protected_route
@limiter.exempt
def organization_dashboard():
    # In reverse chronological order
    CERTIFICATES_ISSUED = MONGODB_DATABASE.CERTIFICATES.find(
        {"certificate_published_by_organization_id": session.get("userID")}
    ).sort("certificate_published_at", -1)
    return (
        render_template(
            "frontend/organization-dashboard.html",
            CERTIFICATES_ISSUED=CERTIFICATES_ISSUED,
        ),
        200,
    )


@app.route("/superuser/dashboard", methods=["GET"])
@superuser_protected_route
@limiter.exempt
def superuser_dashboard():
    return jsonify({"message": "Superuser dashboard"}), 200


# Organization certificate generation routes


@app.route("/organization/certificate/new-batch", methods=["GET"])
@organization_protected_route
@limiter.exempt
def organization_new_certificate_batch():
    return render_template("frontend/organization-new-certificate-batch.html"), 200


# Standalone API routes


@app.route("/api/v1/verify-email", methods=["GET"])
@app.route("/api/v1/user/verify-email", methods=["GET"])
@app.route("/api/v1/organization/verify-email", methods=["GET"])
@limiter.exempt
def api_verify_email():
    if request.args.get("token") is None:
        return (
            jsonify(
                {
                    "message": "Invalid token, please check your email for the correct link",
                    "status": "error",
                }
            ),
            400,
        )

    token = MONGODB_DATABASE.TOKENS.find_one(
        {"token": request.args.get("token"), "token_type": "email_verification"}
    )
    if token is None:
        return (
            jsonify(
                {
                    "message": "Invalid token, please check your email for the correct link",
                    "status": "error",
                },
            ),
            400,
        )

    if token.get("token_used"):
        return (
            jsonify(
                {
                    "message": "This token has already been used, please check your email for the correct link",
                    "status": "error",
                },
            ),
            400,
        )

    if token.get("token_expires_at") < datetime.utcnow():
        return (
            jsonify(
                {
                    "message": "This token has expired, please request a new token by <a href='/sign-in'>signing in</a>",
                    "status": "error",
                }
            ),
            400,
        )

    if token.get("token_for") == "user":
        MONGODB_DATABASE.USERS.update_one(
            {"email": token.get("email")}, {"$set": {"email_verified": True}}
        )
    elif token.get("token_for") == "organization":
        MONGODB_DATABASE.ORGANIZATIONS.update_one(
            {"email": token.get("email")}, {"$set": {"email_verified": True}}
        )
    else:
        return (
            jsonify(
                {
                    "message": "Invalid token, please check your email for the correct link",
                    "status": "error",
                }
            ),
            400,
        )

    MONGODB_DATABASE.TOKENS.update_one(
        {"token": request.args.get("token")}, {"$set": {"token_used": True}}
    )

    return (
        redirect(
            url_for(
                "sign_in",
                message="Your email has been verified successfully, you can now continue to sign in",
            )
        ),
        302,
    )


@app.route("/api/v1/csv-to-json", methods=["POST"])
@limiter.limit("30 per minute")
def api_csv_to_json():
    if request.files.get("csv-file") is None:
        return (
            jsonify(
                {
                    "message": "Please provide a CSV file to convert",
                    "status": "error",
                }
            ),
            400,
        )

    if request.files.get("csv-file").filename.split(".")[-1] != "csv":
        return (
            jsonify(
                {
                    "message": "Please provide a CSV file to convert",
                    "status": "error",
                }
            ),
            400,
        )

    try:
        # Have a json strcuture where the key is the column name and the value is the values of all items in that column

        csv_dict = {}

        csv_file = (
            request.files.get("csv-file")
            .read()
            .decode("utf-8")
            .replace("\r", "")
            .split("\n")
        )

        csv_dict["columns"] = csv_file[0].split(",")

        csv_dict["data"] = []

        for i in csv_file[1:]:
            if len(i) > 0:
                csv_dict["data"].append(i.split(","))

        certificate_details = MONGODB_DATABASE.CERTIFICATE_TEMPLATES.find_one(
            {"_id": bson.ObjectId(request.form.get("certificateID"))}
        )

        if certificate_details is None:
            return (
                jsonify(
                    {
                        "message": "Invalid certificate ID, please check the link and try again",
                        "status": "error",
                    }
                ),
                400,
            )
        
        print(csv_dict.get("columns"), certificate_details.get("certificate_fields"))

        for field_detail in certificate_details.get("certificate_fields"):
            if (
                certificate_details.get("certificate_fields")[field_detail]["name"]
            ) not in csv_dict.get("columns"):
                return (
                    jsonify(
                        {
                            "message": f"The CSV file does not contain the required field {certificate_details.get('certificate_fields')[field_detail]['name']}, please check the file and try again",
                            "status": "error",
                        }
                    ),
                    400,
                )

        return (
            jsonify(
                {
                    "message": "The CSV file was converted successfully",
                    "status": "success",
                    "data": csv_dict,
                }
            ),
            200,
        )

    except Exception as e:
        print(e)
        return (
            jsonify(
                {
                    "message": "Unable to convert the CSV file, please check the file and try again",
                    "status": "error",
                }
            ),
            400,
        )


# Error handlers


@app.errorhandler(400)
def bad_request(error):
    return (
        jsonify(
            {
                "message": "The request was invalid or cannot be otherwise served",
                "status": "error",
            }
        ),
        400,
    )


@app.errorhandler(401)
def unauthorized(error):
    return (
        jsonify(
            {
                "message": "The request requires the user to authenticate, please <a href='/sign-in'>sign in</a> to continue",
                "status": "error",
            }
        ),
        401,
    )


@app.errorhandler(403)
def forbidden(error):
    return (
        jsonify(
            {
                "message": "The current privelage level is insufficient to access this resource",
                "status": "error",
            }
        ),
        403,
    )


@app.errorhandler(404)
def not_found(error):
    return (
        jsonify(
            {
                "message": "The requested resource could not be found or may have been removed",
                "status": "error",
            }
        ),
        404,
    )


@app.errorhandler(405)
def method_not_allowed(error):
    return (
        jsonify(
            {
                "message": "The request method is not supported for the resource",
                "status": "error",
            }
        ),
        405,
    )


@app.errorhandler(429)
def too_many_requests(error):
    return (
        jsonify(
            {
                "message": "Too many requests received, please wait for a while before trying again",
                "status": "error",
            }
        ),
        429,
    )


if __name__ == "__main__":
    app.run(
        host=APP_CONFIG["HOST"],
        port=APP_CONFIG["PORT"],
        debug=APP_CONFIG["DEBUG"],
    )
