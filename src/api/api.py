import os
import pickle
import re
from typing import Any, Dict, List, Union

import langchain
from fastapi import FastAPI
from langchain.chains import (ConversationChain, RetrievalQA,
                              create_history_aware_retriever,
                              create_retrieval_chain)
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.docstore.document import Document
from langchain.memory import ChatMessageHistory
from langchain.schema import Document
from langchain.vectorstores.base import VectorStoreRetriever
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.prompts import (ChatPromptTemplate, MessagesPlaceholder,
                                    format_document)
from langchain_core.retrievers import BaseRetriever, RetrieverOutput
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from prompts import contextualize_q_system_prompt, qa_system_prompt
from pydantic import BaseModel
from secret import *

os.environ['PINECONE_API_KEY'] = PINECONE_API_KEY
os.environ['OPENAI_API_KEY'] = OPENAI_API_KEY

app = FastAPI()

# enable debugging
# langchain.debug = True


# modify retriever to pass in metadata filtering args
# inspired by https://github.com/langchain-ai/langchain/issues/9195
class VectorStoreRetrieverFilter(VectorStoreRetriever):
    '''Custom vectorstore retriever with filter functionality.'''

    def _get_relevant_documents(self, input) -> List[Document]:
        # Filter is provided
        print(input)
        query = input["input"]
        filter = input.get("filter", None)
        if filter is not None:
            # Only similarity search is implemented for now
            docs = self.vectorstore.max_marginal_relevance_search(
                query, filter=filter, k=3, fetch_k=10)
        else:
            # Filter is not provided
            docs = self.vectorstore.max_marginal_relevance_search(
                query, k=3, fetch_k=10)
        return docs


# slightly modified version of create_retrieval_chain to allow multiple inputs
# https://github.com/langchain-ai/langchain/blob/master/libs/langchain/langchain/chains/retrieval.py
def create_custom_retrieval_chain(
    retriever: Union[BaseRetriever, Runnable[dict, RetrieverOutput]],
    combine_docs_chain: Runnable[Dict[str, Any], str],
) -> Runnable:
    retrieval_docs: Runnable[dict, RetrieverOutput] = retriever

    retrieval_chain = (RunnablePassthrough.assign(
        context=retrieval_docs.with_config(
            run_name="retrieve_documents"), ).assign(
                answer=combine_docs_chain)).with_config(
                    run_name="retrieval_chain")

    return retrieval_chain


def load_ids():
    relevant_ids = None
    with open("ids.pickle", "rb") as handle:
        relevant_ids = pickle.load(handle)
    pattern = re.compile(r"(?=(" +
                         '|'.join(re.escape(item)
                                  for item in relevant_ids) + r"))")
    return pattern


def find_matching_ids(query, pattern):
    matches = pattern.findall(query)
    return list(set(matches)) if matches else None


# match known ids against inputs
id_match_pattern = load_ids()

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
embeddings = OpenAIEmbeddings(model='text-embedding-ada-002', )
vectorstore = PineconeVectorStore(index_name="instalily-oa",
                                  embedding=embeddings)
index = VectorStoreRetrieverFilter(vectorstore=vectorstore)

# Q/A RAG
qa_prompt = ChatPromptTemplate.from_messages([
    ("system", qa_system_prompt),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
])

question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
rag_chain = create_custom_retrieval_chain(index, question_answer_chain)
store = ChatMessageHistory()


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    return store


final_chain = RunnableWithMessageHistory(
    rag_chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="answer",
)


class Message(BaseModel):
    user_query: str


@app.post("/get_ai_message")
async def get_ai_message(message: Message):
    query = message.user_query
    id_matches = find_matching_ids(query, id_match_pattern)

    inputs = {"input": query}
    if id_matches: inputs["filter"] = {"id": {"$in": id_matches}}

    ai_output = final_chain.invoke(
        inputs, config={"configurable": {
            "session_id": "fiwb"
        }})
    if len(store.messages) >= 3:
        store.messages.pop(0)

    return {"role": "assistant", "content": ai_output["answer"]}
