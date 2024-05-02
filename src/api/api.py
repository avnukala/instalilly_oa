from fastapi import FastAPI
from pydantic import BaseModel
from langchain_community.llms import Replicate
from langgraph.graph import END, MessageGraph
from langchain_core.messages import HumanMessage
import os
from secret import REPLICATE_API_KEY
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from scrape.parsing_tools import scrape_model_symptoms, solve_model_symptoms, scrape_part_install, scrape_part_info
from langchain.memory import ConversationBufferWindowMemory
from langchain.agents import create_structured_chat_agent
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad.tools import format_to_tool_messages
from langchain_core.output_parsers import StrOutputParser
from langgraph.graph import END, Graph
from langchain_core.utils.function_calling import convert_to_openai_function
from langchain_core.utils.function_calling import convert_to_openai_function
from typing import TypedDict, Annotated, Sequence
import operator
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolInvocation
import json
from langchain_core.messages import FunctionMessage
from langgraph.prebuilt import ToolExecutor



os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_KEY

app = FastAPI()


tools = [scrape_model_symptoms, solve_model_symptoms, scrape_part_install, scrape_part_info]

# TODO: keep history
# TODO: RAG
# TODO: prompt LLM to ask for model and part number as much as possible
# TODO: Analyze ability to answer multiple questions at once when using tools
# llm = Replicate(
#     model="mistralai/mistral-7b-instruct-v0.2",
#     model_kwargs={
#         "temperature": 0.3,
#         "max_new_tokens": 1024,
#         "top_p": 0.9,
#         "prompt_template": """
#             Always assist with care, respect, and truth. Respond with utmost utility yet securely. Avoid harmful, unethical, prejudiced or negative content. Ensure replies promote fairness and positivity. 
#             You are a chatbot designed to help users with information related to dishwashers and refrigerators from partselect.com.
#             DO NOT discuss anything other than dishwashers and refrigerators with the user.
#             When necessary to provide results, please ask the customer to provide the model ID of their appliance or the part
#             ID of the part.
#             <s>[INST] {prompt} [/INST]"""
#     },
# )

# Main Agent
model = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
system = """Always assist with care, respect, and truth. Respond with utmost utility yet securely. Avoid harmful, unethical, prejudiced or negative content. Ensure replies promote fairness and positivity. 
            You are a chatbot designed to help users with information related to dishwashers and refrigerators from partselect.com.
            DO NOT discuss anything other than dishwashers and refrigerators with the user.
            Please ask the customer to provide the model ID of their appliance or the part ID of the part to use for the tools we have access to."""
main_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("user", "{input}")
    ]
)

functions = [convert_to_openai_function(t) for t in tools]
model = model.bind_functions(functions)
tool_executor = ToolExecutor(tools)

llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0)
system = """You are an identified trained to figure out part / model IDs from human text. All you will do is return the number."""
re_write_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("user", "How can I install part number PS11752778?"),
        ("system", "PS11752778"),
        ("user", "Is this part compatible with my WDT780SAEM1 model?"),
        ("system", "WDT780SAEM1"),
        ("user", {input})
    ]
)


class Message(BaseModel):
    user_query: str
    
    
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    model_id: str
    part_id: str
    
    
workflow = Graph()

def basic_agent(state):
    messages = state['messages']
    response = model.invoke(messages)
    return {"messages": [response]}

# basics: 
# - model queries
# - part queries 
# - general Q/A


def model_queries(state):
    messages = state['messages']
    last_message = messages[-1]
    parsed_tool_input = json.loads(last_message.additional_kwargs["function_call"]["arguments"])
    action = ToolInvocation(
            tool=last_message.additional_kwargs["function_call"]["name"],
            tool_input=parsed_tool_input['__arg1'],
        )
    response = tool_executor.invoke(action)
    function_message = FunctionMessage(content=str(response), name=action.tool)
    return {"messages": [function_message]}


@app.post("/get_ai_message")
async def get_ai_message(message: Message):
    assistant_response = llm.invoke(message.user_query)

    return {
        "role": "assistant",
        "content": assistant_response
    }
