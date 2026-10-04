from fastapi import FastAPI
from vision.pictureMeasurements import router as measure_router

app = FastAPI()

app.include_router(measure_router)

@app.get("/")
def read_root():
    return {"message": "Hello World"}
