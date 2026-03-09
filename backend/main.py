from fastapi import FastAPI, UploadFile, File

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Genomic API is running"}


@app.post("/upload-dna/")
async def upload_dna(file: UploadFile = File(...)):

    contents = await file.read()

    return {
        "filename": file.filename,
        "size": len(contents)
    }