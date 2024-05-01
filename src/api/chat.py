# from langchain.chains import LLMChain
# from langchain_community.llms import Replicate
# from langchain_core.prompts import PromptTemplate
# import os
# from secret import REPLICATE_API_KEY
# import replicate

# os.environ["REPLICATE_API_TOKEN"] = REPLICATE_API_KEY


# input = {
#     "top_k": 50,
#     "top_p": 0.9,
#     "prompt": "I have to peel 10+ heads of garlic. What's the best way to all the cloves out of a head of garlic?",
#     "temperature": 0.6,
#     "max_new_tokens": 512,
#     "prompt_template": "<s>[INST] {prompt} [/INST] "
# }

# for event in replicate.stream(
#     "mistralai/mistral-7b-instruct-v0.2",
#     input=input
# ):