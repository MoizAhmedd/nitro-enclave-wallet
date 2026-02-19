from fastapi import FastAPI
from pydantic import BaseModel
import socket
import json

app = FastAPI()

ENCLAVE_CID = 20  # update after running enclave
ENCLAVE_PORT = 5000

def send_to_enclave(request: dict) -> dict:
    sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
    sock.connect((ENCLAVE_CID, ENCLAVE_PORT))
    sock.send(json.dumps(request).encode())
    response = sock.recv(4096).decode()
    sock.close()
    return json.loads(response)

@app.get("/public-key")
def get_public_key():
    return send_to_enclave({"action": "get_public_key"})

class SignRequest(BaseModel):
    message: str  # hex-encoded

@app.post("/sign")
def sign_message(req: SignRequest):
    return send_to_enclave({"action": "sign", "message": req.message})

@app.get("/health")
def health():
    return {"status": "ok"}
