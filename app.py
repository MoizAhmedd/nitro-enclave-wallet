import socket
import json
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, Prehashed
from Crypto.Hash import keccak

# Generate secp256k1 keypair on startup
private_key = ec.generate_private_key(ec.SECP256K1(), default_backend())
public_key = private_key.public_key()

# Get uncompressed public key bytes (65 bytes: 0x04 || x || y)
pub_bytes = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)

# Derive Ethereum address: keccak256(pubkey[1:])[-20:]
def get_eth_address(pub_bytes: bytes) -> str:
    k = keccak.new(digest_bits=256)
    k.update(pub_bytes[1:])  # skip 0x04 prefix
    return "0x" + k.digest()[-20:].hex()

eth_address = get_eth_address(pub_bytes)

print(f"Enclave started.", flush=True)
print(f"Public key: {pub_bytes.hex()}", flush=True)
print(f"Ethereum address: {eth_address}", flush=True)

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
            response = {
                "public_key": pub_bytes.hex(),
                "address": eth_address
            }
        
        elif request.get("action") == "sign":
            # Expects pre-hashed message (32 bytes, hex-encoded)
            msg_hash = bytes.fromhex(request["message"])
            signature = private_key.sign(msg_hash, ec.ECDSA(Prehashed(hashes.SHA256())))
            r, s = decode_dss_signature(signature)
            
            # Normalize s to lower half of curve (EIP-2)
            n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
            if s > n // 2:
                s = n - s
            
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
