"""HTTP wrapper around the geometry module. Contracts: contract.md (in), contract_output.md (out).

    uvicorn api:app --reload --port 8000        # then open http://localhost:8000/docs

Env: ALLOWED_ORIGINS = comma-separated list of frontend origins (default "*": any origin).
"""
import logging
import os

from fastapi import Body, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from geometry.build import build_from_contract
from geometry.lens import GeometryError

log = logging.getLogger("optiframe")

app = FastAPI(title="OptiFrame geometry API", version="1")

origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST"],
                   allow_headers=["*"])

def _error(status, code, message):
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message}})

@app.exception_handler(RequestValidationError)
async def _bad_request(request, exc):
    """Body missing, not valid JSON, or not a JSON object: answer in our error format."""
    return _error(422, "bad_request", "The request could not be read. Send a JSON object.")

@app.post("/frame")
def frame(data: dict = Body(...)):
    """Contract input in, STL (base64) + report out. 422 + error JSON when the input is rejected.
    A plain `def` so FastAPI runs the (CPU-bound) build in a worker thread, not on the event loop."""
    try:
        _, response = build_from_contract(data)
    except GeometryError as e:
        return JSONResponse(status_code=422, content=e.to_dict())
    except Exception:
        log.exception("frame build failed")
        return _error(500, "internal", "The frame could not be built. Retake the photo or try again.")
    return response