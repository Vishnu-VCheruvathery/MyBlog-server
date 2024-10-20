import pymongo
from bson import ObjectId  # bson is a PyMongo library for handling ObjectId
import os
url =  os.environ.get("MONGO_URL")
client = pymongo.MongoClient(url)

db = client['BlogSite']
blog_collection = db['blogs']  
user_collection = db['users']
