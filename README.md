# nitro-enclave-wallet

A cryptographic signing service that runs inside an [AWS Nitro Enclave](https://aws.amazon.com/ec2/nitro/nitro-enclaves/), keeping private keys isolated from the parent EC2 instance.

## How It Works

The enclave generates a SECP256R1 (P-256) keypair on startup and exposes a signing API over [vsock](https://docs.aws.amazon.com/enclaves/latest/user/nitro-enclave-concepts.html). The private key never leaves the enclave — only the public key and signatures are returned to the caller.

```
┌──────────────────────────┐
│     EC2 Instance         │
│                          │        vsock (CID, Port:5000)
│     client.py ───────────┼──────────────────────┐
│                          │                      │
└──────────────────────────┘                      ▼
                                    ┌──────────────────────────┐
                                    │     Nitro Enclave        │
                                    │                          │
                                    │     app.py               │
                                    │     - Generates keypair  │
                                    │     - Signs messages     │
                                    │     - Returns pub key    │
                                    └──────────────────────────┘
```

## API

The enclave accepts JSON requests over vsock on port 5000.

**Get public key:**

```json
{"action": "get_public_key"}
// Response: {"public_key": "<hex-encoded X962 uncompressed>"}
```

**Sign a message:**

```json
{"action": "sign", "message": "<hex-encoded bytes>"}
// Response: {"r": "<hex>", "s": "<hex>"}
```

Signatures use ECDSA with SHA-256.

## Prerequisites

- An EC2 instance with [Nitro Enclaves enabled](https://docs.aws.amazon.com/enclaves/latest/user/create-enclave.html)
- [Nitro CLI](https://docs.aws.amazon.com/enclaves/latest/user/nitro-enclave-cli.html) installed
- Docker

## Build & Run

Build the Docker image and convert it to an enclave image:

```bash
docker build -t nitro-enclave-wallet .

nitro-cli build-enclave --docker-uri nitro-enclave-wallet:latest --output-file nitro-enclave-wallet.eif
```

Run the enclave:

```bash
nitro-cli run-enclave --eif-path nitro-enclave-wallet.eif --cpu-count 2 --memory 1200

# Get the enclave CID
nitro-cli describe-enclaves
```

Update the CID in `client.py` to match the running enclave's CID before testing.

Test from the parent instance:

```bash
python3 client.py
```

## Project Structure

```
app.py          # Enclave server — key generation, signing, vsock listener
client.py       # Test client — connects to enclave and exercises the API
Dockerfile      # Amazon Linux 2023 container with Python + cryptography
```
