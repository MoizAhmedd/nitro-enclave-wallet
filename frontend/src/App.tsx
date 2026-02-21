import { useEffect, useState } from 'react'
import {
  createPublicClient,
  http,
  formatEther,
  parseEther,
  serializeTransaction,
  keccak256,
  recoverAddress,
  type TransactionSerializableEIP1559,
  type Hex,
} from 'viem'
import { sepolia } from 'viem/chains'
import './App.css'

const publicClient = createPublicClient({
  chain: sepolia,
  transport: http(),
})

function App() {
  const [address, setAddress] = useState<Hex | null>(null)
  const [balance, setBalance] = useState<string | null>(null)
  const [recipient, setRecipient] = useState('')
  const [amount, setAmount] = useState('')
  const [txHash, setTxHash] = useState<string | null>(null)
  const [status, setStatus] = useState<{ message: string; type: 'loading' | 'error' | 'success' } | null>(null)

  // Fetch address on mount
  useEffect(() => {
    fetchAddress()
  }, [])

  // Fetch balance when address changes
  useEffect(() => {
    if (address) {
      fetchBalance(address)
    }
  }, [address])

  async function fetchAddress() {
    try {
      const resp = await fetch('/api/address')
      if (!resp.ok) throw new Error(`Server error: ${resp.status}`)
      const data = await resp.json()
      setAddress(data.address as Hex)
    } catch (err) {
      setStatus({ message: `Failed to fetch address: ${err}`, type: 'error' })
    }
  }

  async function fetchBalance(addr: Hex) {
    try {
      const bal = await publicClient.getBalance({ address: addr })
      setBalance(formatEther(bal))
    } catch (err) {
      setStatus({ message: `Failed to fetch balance: ${err}`, type: 'error' })
    }
  }

  async function handleSend() {
    if (!address) return
    setTxHash(null)
    setStatus({ message: 'Building transaction...', type: 'loading' })

    try {
      const to = recipient as Hex
      const value = parseEther(amount)

      // Get nonce and gas prices
      const [nonce, block] = await Promise.all([
        publicClient.getTransactionCount({ address }),
        publicClient.getBlock(),
      ])

      const baseFee = block.baseFeePerGas ?? 0n
      const maxPriorityFeePerGas = 1_000_000_000n // 1 gwei
      const maxFeePerGas = baseFee * 2n + maxPriorityFeePerGas

      const tx: TransactionSerializableEIP1559 = {
        type: 'eip1559',
        chainId: sepolia.id,
        nonce,
        maxPriorityFeePerGas,
        maxFeePerGas,
        gas: 21000n,
        to,
        value,
        data: '0x',
      }

      // Serialize unsigned tx and hash it
      setStatus({ message: 'Signing transaction...', type: 'loading' })
      const serialized = serializeTransaction(tx)
      const hash = keccak256(serialized)

      // Send hash to enclave for signing
      const signResp = await fetch('/api/sign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: hash.slice(2) }), // remove 0x prefix
      })
      if (!signResp.ok) throw new Error(`Sign error: ${signResp.status}`)
      const sig = await signResp.json()

      const r = sig.r.startsWith('0x') ? sig.r : ('0x' + sig.r) as Hex
      const s = sig.s.startsWith('0x') ? sig.s : ('0x' + sig.s) as Hex

      // Recover yParity by trying both 0 and 1
      setStatus({ message: 'Recovering signature...', type: 'loading' })
      let yParity: 0 | 1 | undefined
      for (const v of [0, 1] as const) {
        try {
          const recovered = await recoverAddress({
            hash,
            signature: { r, s, yParity: v },
          })
          if (recovered.toLowerCase() === address.toLowerCase()) {
            yParity = v
            break
          }
        } catch {
          continue
        }
      }

      if (yParity === undefined) {
        throw new Error('Could not recover valid yParity from signature')
      }

      // Assemble signed tx
      const signedTx = serializeTransaction(tx, { r, s, yParity })

      // Broadcast
      setStatus({ message: 'Broadcasting transaction...', type: 'loading' })
      const txHashResult = await publicClient.sendRawTransaction({
        serializedTransaction: signedTx,
      })

      setTxHash(txHashResult)
      setStatus({ message: 'Transaction sent!', type: 'success' })

      // Refresh balance after a short delay
      setTimeout(() => fetchBalance(address), 3000)
    } catch (err) {
      setStatus({ message: `Transaction failed: ${err}`, type: 'error' })
    }
  }

  return (
    <>
      <h1>Nitro Enclave Wallet</h1>
      <p style={{ color: '#888', marginTop: 0 }}>Sepolia Testnet</p>

      <div className="wallet-info">
        <p>
          <span className="label">Address: </span>
          <span className="address-value">{address ?? 'Loading...'}</span>
        </p>
        <p>
          <span className="label">Balance: </span>
          <span className="address-value">{balance !== null ? `${balance} ETH` : 'Loading...'}</span>
        </p>
      </div>

      <div className="send-form">
        <input
          type="text"
          placeholder="Recipient address (0x...)"
          value={recipient}
          onChange={(e) => setRecipient(e.target.value)}
        />
        <input
          type="text"
          placeholder="Amount (ETH)"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
        />
        <button
          onClick={handleSend}
          disabled={!address || !recipient || !amount || status?.type === 'loading'}
        >
          {status?.type === 'loading' ? 'Sending...' : 'Send ETH'}
        </button>
      </div>

      {status && (
        <div className={`status ${status.type}`}>
          {status.message}
        </div>
      )}

      {txHash && (
        <div className="status success">
          <a
            href={`https://sepolia.etherscan.io/tx/${txHash}`}
            target="_blank"
            rel="noopener noreferrer"
          >
            View on Etherscan
          </a>
        </div>
      )}
    </>
  )
}

export default App
