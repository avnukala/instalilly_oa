import pickle

import jsonlines
import numpy as np
import tiktoken
from openai import OpenAI
from pinecone import Pinecone
from secret import *
from tqdm import tqdm

openai_client = OpenAI(api_key=OPENAI_API_KEY)
pc = Pinecone(api_key=PINECONE_API_KEY)


def num_tokens_from_string(token_stats, string: str, encoding_name: str) -> int:
    """Returns the number of tokens in a text string."""
    encoding = tiktoken.get_encoding(encoding_name)
    num_tokens = len(encoding.encode(string))
    token_stats.append(num_tokens)
    return token_stats


def get_embedding(doc):
	response = openai_client.embeddings.create(
    	model= "text-embedding-ada-002",
    	input=[doc]
	)
	embedding = response.data[0].embedding
    
	return embedding


# improvements for extensibility: parallelize upserts and embeds into batches
def vectorize_json(batch_size, stats=True):
    index = pc.Index("instalily-oa")
    token_stats = []
    id_number = 1 # no idea if id number is significant or not for Pinecone
    batch_metadata = []
    batch_embeddings = []
    relevant_ids = set()
    
    with jsonlines.open('data.jsonl') as reader:
        for obj in tqdm(reader):
            doc = ''
            metadata = {'id': []}
            for key, value in obj.items():
                doc += f"{key}: {value} "
                match key:
                    case "Model Number": metadata["id"].append(value)
                    case "PartSelect Number": metadata["id"].append(value)
                    case "Manufacturer Part Number": metadata["id"].append(value)
                    case "Manufacturer": metadata["manufacturer"] = (value)
            metadata['text'] = doc
            relevant_ids.update(metadata["id"])
            embedding = get_embedding(doc)
            batch_metadata.append(metadata)
            batch_embeddings.append(embedding)
            if stats: token_stats = num_tokens_from_string(token_stats, doc, 'cl100k_base')
            
            if len(batch_embeddings) == batch_size:
                batch = []
                
                for embedding, meta in zip(batch_embeddings, batch_metadata):
                    batch.append({
                        "id": str(id_number), "values": embedding, "metadata": meta
                    })
                    id_number += 1
                index.upsert(vectors=batch)
                batch_embeddings = []
                batch_metadata = []
                
                with open("../src/api/ids.pickle", "wb") as handle:
                    pickle.dump(relevant_ids, handle)
            
    if batch_embeddings:
        batch = []
                
        for embedding, meta in zip(batch_embeddings, batch_metadata):
            batch.append({
                "id": str(id_number), "values": embedding, "metadata": meta
            })
            id_number += 1

        index.upsert(vectors = batch)
        
    if stats:
        print(f'Avg Tokens per Doc: {sum(token_stats) / len(token_stats)}')
        print(f'Max Tokens per Doc: {max(token_stats)}')
        
        
vectorize_json(10)