from langchain.pydantic_v1 import BaseModel, Field


class PartSearch(BaseModel):
    part_id: str = Field(description="should be the 10-digit Part ID String")


class ModelSearch(BaseModel):
    model_id: str = Field(description="should be the 10-digit Refridgerator or Dishwasher Model ID String")


class SymptomSearch(BaseModel):
    model_id: str = Field(description="should be the 10-digit Refridgerator or Dishwasher Model ID String")
    user_input: str = Field(description="the customer's description of the problem with their appliance")
