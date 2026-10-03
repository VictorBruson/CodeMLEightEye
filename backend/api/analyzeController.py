import shutil
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from PIL import Image
import io

app = FastAPI()

UPLOAD_DIR = Path("uploaded_images")
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

@app.post("/upload-image/", status_code=status.HTTP_201_CREATED)
async def upload_and_save_image(file: UploadFile = File(...)):
    # 1. Validate file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file extension '{file_ext}'."
        )

    # 2. Read bytes and validate that it's a valid image using Pillow
    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))
        image.verify()  # Verify image integrity
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid or corrupted image."
        )

    return {
        "message": "Image uploaded successfully",
    }