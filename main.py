import base64
import os

import fitz  # pymupdf
import pymupdf4llm
from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from pydantic import BaseModel

app = FastAPI(title="PDF Text Extractor for Tenderbot")

# API Key authentication
API_KEY = os.environ.get("API_KEY")

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_BATCH_FILES = 10


class BatchFile(BaseModel):
    filename: str
    content: str  # base64 encoded PDF


class BatchRequest(BaseModel):
    files: list[BatchFile]


async def verify_api_key(x_api_key: str = Header(None)):
    """Verify API key if one is configured."""
    if API_KEY is None:
        # No API key configured, allow all requests (for local dev)
        return True
    if x_api_key is None or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


def extract_text_from_pdf(pdf_bytes: bytes, filename: str) -> dict:
    """Extract markdown-formatted text from PDF bytes, returns structured result."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception:
        raise HTTPException(
            status_code=400, detail=f"Could not open '{filename}' as a valid PDF"
        )

    num_pages = len(doc)

    # Full document as markdown (preserves headers, tables, structure)
    full_text = pymupdf4llm.to_markdown(doc).strip()

    # Per-page extraction
    pages_text = []
    for page_num in range(num_pages):
        page_md = pymupdf4llm.to_markdown(doc, pages=[page_num]).strip()
        pages_text.append({"page": page_num + 1, "text": page_md})

    doc.close()

    return {
        "filename": filename,
        "pages": num_pages,
        "total_characters": len(full_text),
        "text": full_text,
        "pages_text": pages_text,
    }


@app.post("/extract")
async def extract(
    file: UploadFile = File(...),
    authenticated: bool = Depends(verify_api_key),
):
    """Extract text from a single PDF file."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    pdf_bytes = await file.read()

    if len(pdf_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 50MB limit")

    return extract_text_from_pdf(pdf_bytes, file.filename)


@app.post("/extract-multiple")
async def extract_multiple(
    files: list[UploadFile] = File(...),
    authenticated: bool = Depends(verify_api_key),
):
    """Extract text from multiple PDF files."""
    documents = []

    for file in files:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400, detail=f"File '{file.filename}' is not a PDF"
            )

        pdf_bytes = await file.read()

        if len(pdf_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' exceeds 50MB limit",
            )

        result = extract_text_from_pdf(pdf_bytes, file.filename)
        # Exclude pages_text for multi-file to keep response compact
        documents.append(
            {
                "filename": result["filename"],
                "pages": result["pages"],
                "total_characters": result["total_characters"],
                "text": result["text"],
            }
        )

    return {"documents": documents}


@app.post("/extract-batch")
async def extract_batch(
    request: BatchRequest,
    authenticated: bool = Depends(verify_api_key),
):
    """Extract text from multiple base64-encoded PDF files."""
    if len(request.files) > MAX_BATCH_FILES:
        raise HTTPException(
            status_code=400, detail=f"Maximum {MAX_BATCH_FILES} files per request"
        )

    documents = []

    for item in request.files:
        try:
            pdf_bytes = base64.b64decode(item.content)
        except Exception:
            documents.append(
                {"filename": item.filename, "error": "Invalid base64 content"}
            )
            continue

        if len(pdf_bytes) > MAX_FILE_SIZE:
            documents.append(
                {"filename": item.filename, "error": "File exceeds 50MB limit"}
            )
            continue

        try:
            result = extract_text_from_pdf(pdf_bytes, item.filename)
            documents.append(
                {
                    "filename": result["filename"],
                    "pages": result["pages"],
                    "total_characters": result["total_characters"],
                    "text": result["text"],
                }
            )
        except HTTPException as e:
            documents.append({"filename": item.filename, "error": e.detail})

    return {"documents": documents}


@app.get("/health")
async def health_check():
    return {"status": "ok"}
