from fastapi import FastAPI
from api.generate import app as frame_app
from vision.pictureMeasurements import router as measure_router

app = FastAPI()

app.include_router(measure_router)
app.mount("/api", frame_app)

@app.get("/")
def read_root():
    return {"message": "Hello World"}
