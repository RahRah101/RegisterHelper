from pydantic import BaseModel


class Term(BaseModel):
    code: str
    description: str
