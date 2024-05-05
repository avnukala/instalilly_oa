from pinecone import Pinecone
from secret import *
import jsonlines

pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("instalily-oa")

def convert_json2text(data):
    