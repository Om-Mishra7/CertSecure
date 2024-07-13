import os
from dotenv import load_dotenv
import json
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient
from beem import Steem
from beem.account import Account
from beem.exceptions import ContentDoesNotExistsException
from flask import Flask, request, jsonify

load_dotenv()

CLIENT = MongoClient(os.environ.get("MONGODB_URI"))
DATABASE = CLIENT["CERTSECURE-DATABASE"]


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o)
        elif isinstance(o, datetime):
            return o.isoformat()
        return super().default(o)   


# Define the hive.io credentials
posting_key = os.environ.get("HIVE_POSTING_KEY")
account_name = os.environ.get("HIVE_ACCOUNT_NAME")

# Connect to the Hive blockchain
steem = Steem(keys=[posting_key])


# Define the function to upload JSON data as a string referenced by a unique ID
def add_certificate(unique_id, json_data):
    # Convert ObjectId to string
    try:
        unique_id_str = str(unique_id)
        steem.custom_json(
            id=unique_id_str,
            json_data=json_data,
            required_posting_auths=[account_name],
        )
        return True
    except Exception as e:
        print(e)
        return False


# Define the function to retrieve data back using the unique ID
def retrieve_json_data(unique_id):
    try:
        account = Account(account_name, steem_instance=steem)
        history = account.history(only_ops=["custom_json"])
        for op in history:
            if (json.loads(op["json"]).get("_id")) == unique_id:
                data = json.loads(op["json"])
                return True, data
    except ContentDoesNotExistsException:
        return False, None


# Define the Flask app

app = Flask(__name__)

@app.route("/", methods=["GET"])
def home_route():
    return jsonify({"status": "success", "message": "Welcome to CertSecure!"})


@app.route("/add-certificate/<unique_id>", methods=["POST"])
def add_certificate_route(unique_id):
    certificate_data = DATABASE["CERTIFICATES"].find_one({"_id": ObjectId(unique_id)})
    if certificate_data is None:
        return jsonify({"status": "error", "message": "Certificate not found!"})

    if certificate_data["certificate_publsihing_status"] != "pending":
        return jsonify(
            {"status": "success", "message": "Certificate already published!"}
        )

    if add_certificate(unique_id, json.dumps(certificate_data, cls=CustomJSONEncoder)):
        DATABASE["CERTIFICATES"].update_one(
            {"_id": ObjectId(unique_id)},
            {"$set": {"certificate_publsihing_status": "published"}},
        )
        return jsonify(
            {"status": "success", "message": "Certificate published successfully!"}
        )
    else:
        return jsonify({"status": "error", "message": "Failed to publish certificate!"})


@app.route("/get-certificate/<unique_id>", methods=["GET"])
def get_certificate_route(unique_id):
    success, data = retrieve_json_data(unique_id)
    if success:
        return jsonify({"status": "success", "data": data})
    else:
        return jsonify({"status": "error", "message": "Certificate not found!"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
