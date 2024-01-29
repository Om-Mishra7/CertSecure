import time
from pymongo.mongo_client import MongoClient
import redis


def connect_monogodb(HOST, DATABASE):
    try:
        CLIENT = MongoClient(host=HOST)
        DATABASE = CLIENT[DATABASE]
        return DATABASE
    except Exception as e:
        raise Exception(
            "The server was not able to connect to the MONGODB database with error: {}".format(
                e
            )
        )


def connect_redis(HOST):
    try:
        CLIENT = redis.from_url(url=HOST)
        CLIENT.ping()
        return CLIENT
    except Exception as e:
        raise Exception(
            "The server was not able to connect to the REDIS database with error: {}".format(
                e
            )
        )
