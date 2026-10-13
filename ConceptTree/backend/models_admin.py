from pydantic import BaseModel, Field


class AdminSessionRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)
