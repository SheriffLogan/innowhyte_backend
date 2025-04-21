from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from app.utils.utils import *
import os, uuid
from app.schema.schema_classes import *


router = APIRouter()

UPLOAD_DIR = "uploads"
SUMMARY_DIR = "summaries"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(SUMMARY_DIR, exist_ok=True)

@router.get("/", summary="Health check", tags=["Health"])
async def health_check():
    """
    A simple endpoint to verify that the server is up and running.
    """
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "message": "Document Analyzer service is healthy"}
    )


@router.get("/pdfs", response_model=List[PDFSummary])
def list_pdfs():
    files = []
    try:
        for filename in os.listdir(UPLOAD_DIR):
            # Attempt to split the filename into file_id and original name using the first underscore.
            match = re.match(r'^([^_]+)_(.+)$', filename)
            if match:
                file_id = match.group(1)
                original_name = match.group(2)
            else:
                file_id = filename
                original_name = filename
            # Avoid duplicates: only add unique original file names.
            if not any(f.get("name") == original_name for f in files):
                files.append({
                    "id": file_id,
                    "name": original_name
                })
        return JSONResponse(content=files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing PDFs: {str(e)}")


@router.post("/upload-pdf")
async def gemini_doc_summary(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading file: {str(e)}")
    
    # Generate a unique file ID and store the file with its original name.
    file_id = str(uuid.uuid4())
    new_filename = f"{file_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)
    try:
        with open(file_path, "wb") as f:
            f.write(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
    
    async def summary_stream():
        try:
            for update in gemini_stream_document_summary(pdf_bytes):
                # Each update is a JSON string from our pydantic model.
                yield f"data: {update}\n\n"
        except Exception as e:
            yield f"data: {ErrorResponse(message=str(e)).json()}\n\n"

    return StreamingResponse(summary_stream(), media_type="text/event-stream")