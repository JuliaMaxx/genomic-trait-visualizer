import os

from fastapi import FastAPI, File, UploadFile

from genomics.dna_parser import parse_dna_file

app = FastAPI()

UPLOADED_FOLDER = "uploads"

os.makedirs(UPLOADED_FOLDER, exist_ok=True)


@app.post("/upload-dna/")
async def upload_dna(file: UploadFile = File(...)):

    file_path = os.path.join(UPLOADED_FOLDER, file.filename)

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    variants = parse_dna_file(file_path)

    return {"filename": file.filename, "variants": variants[:10]}
