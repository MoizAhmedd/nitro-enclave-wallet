import socket
import json
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

# Generate keypair on startup
private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
public_key = private_key.public_key()

pub_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

print(f"Enclave started. Public key: {pub_bytes.hex()}", flush=True)

# vsock server
CID = socket.VMADDR_CID_ANY
PORT = 5000

sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
sock.bind((CID, PORT))
sock.listen(1)

print(f"Listening on vsock port {PORT}...", flush=True)

while True:
    conn, addr = sock.accept()
    print(f"Connection from {addr}", flush=True)
    
    try:
        data = conn.recv(4096).decode()
        request = json.loads(data)
        
        if request.get("action") == "get_public_key":
            response = {"public_key": pub_bytes.hex()}
        
        elif request.get("action") == "sign":
            message = bytes.fromhex(request["message"])
            signature = private_key.sign(message, ec.ECDSA(hashes.SHA256()))
            r, s = decode_dss_signature(signature)
            response = {
                "r": hex(r),
                "s": hex(s)
            }
        
        else:
            response = {"error": "unknown action"}
        
        conn.send(json.dumps(response).encode())
    
    except Exception as e:
        conn.send(json.dumps({"error": str(e)}).encode())
    
    finally:
        conn.close()
