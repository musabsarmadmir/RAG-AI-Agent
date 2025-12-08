from pydantic import BaseModel, Field
from typing import List, Optional

class UploadStatus(BaseModel):
    status: str
    path: str

class HealthProvider(BaseModel):
    name: str
    has_index: bool

class HealthResponse(BaseModel):
    status: str
    providers: List[HealthProvider] = []

class QueryRequest(BaseModel):
    client_id: int = Field(..., ge=1)
    question: str = Field(..., min_length=3, max_length=4000)
    top_k: Optional[int] = Field(default=5, ge=1, le=20)

class QuerySource(BaseModel):
    key: str

class QueryResponse(BaseModel):
    answer: str
    sources: List[str]
