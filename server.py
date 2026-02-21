from fastapi import FastAPI
from pydantic import BaseModel
import socket
import json

app = FastAPI()

ENCLAVE_CID = 18
ENCLAVE_PORT = 5000

def send_to_enclave(request: dict) -> dict:
    sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
    sock.connect((ENCLAVE_CID, ENCLAVE_PORT))
    sock.send(json.dumps(request).encode())
    response = sock.recv(4096).decode()
    sock.close()
    return json.loads(response)

@app.get("/address")
def get_address():
    return send_to_enclave({"action": "get_public_key"})

@app.get("/health")
def health():
    return {"status": "ok"}

class SignRequest(BaseModel):
    message: str  # hex-encoded, 32-byte hash

@app.post("/sign")
def sign_message(req: SignRequest):
    return send_to_enclave({"action": "sign", "message": req.message})
