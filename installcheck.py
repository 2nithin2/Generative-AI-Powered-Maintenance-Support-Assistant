import transformers
import openai
import sqlalchemy
import redis
import kafka
import json

print("Libraries imported successfully!")


try:
    redis_cache = redis.Redis(host="localhost", port=6379)
    # Test connection
    redis_cache.ping()
    print("Connected to Redis")
except redis.ConnectionError as e:
    print("Could not connect to Redis:", e)
