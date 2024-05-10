import os
import pickle
import re
from typing import Any, Dict, List, Set, Union

import langchain
from fastapi import FastAPI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.docstore.document import Document
from langchain.memory import ChatMessageHistory
from langchain.schema import Document
from langchain.vectorstores.base import VectorStoreRetriever
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.retrievers import BaseRetriever, RetrieverOutput
from langchain_core.runnables import Runnable, RunnablePassthrough
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from prompts import *
from pydantic import BaseModel
from secret import *

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

app = FastAPI()

# enable debugging
langchain.debug = True


class Message(BaseModel):
    user_query: str


# modify retriever to pass in metadata filtering args
# inspired by https://github.com/langchain-ai/langchain/issues/9195
class VectorStoreRetrieverFilter(VectorStoreRetriever):
    """Custom vectorstore retriever with filter functionality."""

    def _get_relevant_documents(self, input) -> List[Document]:
        query = input["input"]
        filter = input.get("filter", None)  # provide filter
        if filter is not None:
            # decided not to use MMR because returned documents should be similar
            # e.g. If we ask about part solutions, we should only get solutions
            docs = self.vectorstore.similarity_search(query, filter=filter, k=5)
        else:
            # if no filter is provided, we should look for more diverse documents
            docs = self.vectorstore.max_marginal_relevance_search(
                query, k=5, fetch_k=10
            )
        return docs


# slightly modified version of create_retrieval_chain to allow multiple inputs
# https://github.com/langchain-ai/langchain/blob/master/libs/langchain/langchain/chains/retrieval.py
def create_custom_retrieval_chain(
    retriever: Union[BaseRetriever, Runnable[dict, RetrieverOutput]],
    combine_docs_chain: Runnable[Dict[str, Any], str],
) -> Runnable:
    retrieval_docs: Runnable[dict, RetrieverOutput] = retriever

    retrieval_chain = (
        RunnablePassthrough.assign(
            context=retrieval_docs.with_config(run_name="retrieve_documents"),
        ).assign(answer=combine_docs_chain)
    ).with_config(run_name="retrieval_chain")

    return retrieval_chain


class FilterIDs:
    """Class to manage vectorstore filters against part/model ID"""

    filters: Set[str]
    pattern: re.Pattern

    def __init__(self):
        self.pattern = self.load_ids()
        self.filters = set()

    def load_ids(self):
        relevant_ids = None
        with open("ids.pickle", "rb") as handle:
            relevant_ids = pickle.load(handle)
        pattern = re.compile(
            r"(?=(" + "|".join(re.escape(item) for item in relevant_ids) + r"))"
        )
        return pattern

    def update_and_get_filters(self, query, history):
        self.filters = set()  # reset filters and search again
        query_matches = self.pattern.findall(query)
        self.filters.update(query_matches)
        if history.messages:
            prev_matches = self.pattern.findall(str(history))
            self.filters.update(prev_matches)
        return list(self.filters) if self.filters else None


llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
summary_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
)
vectorstore = PineconeVectorStore(index_name="instalily-oa", embedding=embeddings)
index = VectorStoreRetrieverFilter(vectorstore=vectorstore)

summary_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", summary_system_prompt),
        ("human", "{input}"),
    ]
)

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# summarize history
summary_chain = summary_prompt | summary_llm | StrOutputParser()
# pass prompt formatted documents into final query
question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
# retrieve documents to pass into QA chain
rag_chain = create_custom_retrieval_chain(index, question_answer_chain)

store = ChatMessageHistory()
filters = FilterIDs()


@app.post("/get_ai_message")
async def get_ai_message(message: Message):
    # keep sliding history window somewhat small for Q/A (prev 3 msgs)
    if len(store.messages) >= 8:
        store.messages = store.messages[2:]

    query = message.user_query
    inputs = {"input": query, "chat_history": store.messages}

    # history aware question formatter
    if store.messages:
        summary_input = {"input": query, "history": str(store)}
        new_query = summary_chain.invoke(summary_input)
        inputs["input"] = new_query

    id_matches = filters.update_and_get_filters(query, store)
    if id_matches:
        inputs["filter"] = {"id": {"$in": id_matches}}

    ai_output = rag_chain.invoke(inputs)
    store.add_user_message(query)
    store.add_ai_message(ai_output["answer"])

    return {"role": "assistant", "content": ai_output["answer"]}
