import requests
import bcrypt
from flask import render_template
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException


def verify_recaptcha(recaptcha_private_key, recaptcha_response_token):
    recaptcha_url = "https://www.google.com/recaptcha/api/siteverify"
    recaptcha_data = {
        "secret": recaptcha_private_key,
        "response": recaptcha_response_token,
    }
    try:
        recaptcha_server_response = requests.post(
            recaptcha_url, data=recaptcha_data, timeout=2
        )
        recaptcha_json = recaptcha_server_response.json()
        return recaptcha_json.get("success")
    except requests.exceptions.RequestException:
        return False


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())


def verify_password(password, hashed_password):
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password)


def send_email(api_key, email_address, type, token=None):
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key["api-key"] = api_key

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )



    if type == "user-registration":
        subject = f"Welcome to CertSecure!"
        sender = {"name": "CertSecure", "email": "noreply@projectrexa.dedyn.io"}
        to = [{"email": email_address, "name": "User"}]
        reply_to = {"email": "certsecure@projectrexa.dedyn.io", "name": "CertSecure"}
        html = render_template(
            "email/user-registration.html", email_address=email_address, token=token
        )
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to, html_content=html, reply_to=reply_to, sender=sender, subject=subject
        )
    elif type == "organization-registration":
        subject = f"Welcome to CertSecure!"
        sender = {"name": "CertSecure", "email": "noreply@projectrexa.dedyn.io"}
        to = [{"email": email_address, "name": "Organization"}]
        reply_to = {"email": "certsecure@projectrexa.dedyn.io", "name": "CertSecure"}
        html = render_template(
            "email/organization-registration.html",
            email_address=email_address,
            token=token,
        )
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to, html_content=html, reply_to=reply_to, sender=sender, subject=subject
        )
        
    elif type == "email-verification":
        subject = f"Verify your email address | CertSecure"
        sender = {"name": "CertSecure", "email": "noreply@projectrexa.dedyn.io"}
        to = [{"email": email_address, "name": "User"}]
        reply_to = {"email": "certsecure@projectrexa.dedyn.io", "name": "CertSecure"}
        html = render_template(
            "email/email-verification.html",
            email_address=email_address,
            token=token,
        )
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to, html_content=html, reply_to=reply_to, sender=sender, subject=subject
        )
        
    elif type == "password-reset":
        subject = f"Reset your password | CertSecure"
        sender = {"name": "CertSecure", "email": "noreply@projectrexa.dedyn.io"}
        to = [{"email": email_address, "name": "User"}]
        reply_to = {"email": "certsecure@projectrexa.dedyn.io", "name": "CertSecure"}
        html = render_template(
            "email/password-reset.html",
            email_address=email_address,
            token=token,
        )
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to, html_content=html, reply_to=reply_to, sender=sender, subject=subject
        )
        
    elif type == "certificate-issued":
        print(email_address)
        subject = f"Certificate Issued | CertSecure"
        sender = {"name": "CertSecure", "email": "noreply@projectrexa.dedyn.io"}
        to = [{"email": email_address, "name": "User"}]
        reply_to = {"email": "certsecure@projectrexa.dedyn.io", "name": "CertSecure"}
        html = render_template(
            "email/certificate-issued.html",
            email_address=email_address,
            token=token,
        )
        send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
            to=to, html_content=html, reply_to=reply_to, sender=sender, subject=subject
        )
        
        
        
                        

        
    else:
        return False

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        return True
    except ApiException as e:
        print("Exception when calling SMTPApi->send_transac_email: %s\n" % e)
        return False
