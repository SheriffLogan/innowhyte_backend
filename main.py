from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.pdf_routes import router as pdf_router

app = FastAPI(
    title = "Document Summarizer",
    description= "Application to summarize documents using Gemini API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pdf_router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)



