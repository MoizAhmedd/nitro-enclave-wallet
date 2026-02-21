import socket
import json

CID = 17  # enclave CID
PORT = 5000

def send_request(request):
    sock = socket.socket(socket.AF_VSOCK, socket.SOCK_STREAM)
    sock.connect((CID, PORT))
    sock.send(json.dumps(request).encode())
    response = sock.recv(4096).decode()
    sock.close()
    return json.loads(response)

# Get public key
print("Getting public key...")
result = send_request({"action": "get_public_key"})
print(f"Public key: {result}")

# Sign a message
print("\nSigning message...")
message = b"hello world"
result = send_request({"action": "sign", "message": message.hex()})
print(f"Signature: {result}")
