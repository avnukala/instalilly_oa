from fastapi import FastAPI
from pydantic import BaseModel
import requests
from langchain_community.llms import Replicate
from langgraph.graph import END, MessageGraph
from langchain_core.messages import HumanMessage
import replicate
import os
from secret import REPLICATE_API_KEY


os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_KEY

app = FastAPI()


# TODO: keep history
# TODO: RAG
# TODO: prompt LLM to ask for model and part number as much as possible
# TODO: Analyze ability to answer multiple questions at once when using tools
llm = Replicate(
    model="mistralai/mistral-7b-instruct-v0.2",
    model_kwargs={
        "temperature": 0.6,
        "max_new_tokens": 1024,
        "top_p": 0.9,
        "system_prompt": """Always assist with care, respect, and truth. 
            Respond with utmost utility yet securely. Avoid harmful, unethical, 
            prejudiced or negative content. Ensure replies promote fairness and 
            positivity. You are a chatbot designed to help users with information 
            related to dishwashers and refrigerators. Do not stray off topic. 
            When necessary to provide results, please ask the customer to provide
            the model id of their appliance or the part id of the part.""",
        "prompt_template": """<s>[INST] {prompt} [/INST]"""
    },
)


class Message(BaseModel):
    user_query: str


@app.post("/get_ai_message")
async def get_ai_message(message: Message):
    assistant_response = llm(message.user_query)

    return {
        "role": "assistant",
        "content": assistant_response
    }
