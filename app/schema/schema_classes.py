from pydantic import BaseModel
from typing import Literal, Optional

class SectionResponse(BaseModel):
    type: Literal["section"] = "section"
    section: str
    summary: str
    page: Optional[int] = None

class ProgressResponse(BaseModel):
    type: str = "progress"
    progress: int

class ErrorResponse(BaseModel):
    type: str = "error"
    message: str

# For GET /pdfs
class PDFSummary(BaseModel):
    id: str
    name: str