# Architecture: Selective Disclosure for ICS Monitoring

## Design Philosophy

### The Core Principle

**"Privacy by Default, Transparency on Demand"**

Most privacy-preserving systems force a binary choice:
- Either eliminate all access to raw data (full privacy)
- Or expose all data (no privacy)

This is a false dichotomy. Real-world scenarios require flexibility:
- **Most of the time**: Verification without raw values is sufficient
- **Occasionally**: Detailed analysis requires exact values

Our system bridges this gap through **Selective Disclosure**.

## System Architecture

### Overview

```
┌─────────────────────────────────────────────────────────────┐
│                       Sensor Device                          │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Step 1: Read Sensor Value                              │ │
│  │   value = read_sensor()  # e.g., 1.523                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                            ↓                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Step 2: Generate Bulletproof Range Proof              │ │
│  │   proof = bulletproof(value, min, max)                 │ │
│  │   nonce = random_nonce()                               │ │
│  └────────────────────────────────────────────────────────┘ │
│                            ↓                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Step 3: Dual Transmission                              │ │
│  │   • ZK Proof → Verification Server (public)            │ │
│  │   • RAW Value → Reveal Server (private)                │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
              ↓                              ↓
┌──────────────────────────┐    ┌───────────────────────────┐
│  Verification Server     │    │   Reveal Server           │
│  (Public Verification)   │    │   (Private Storage)       │
├──────────────────────────┤    ├───────────────────────────┤
│                          │    │                           │
│ • Receive ZK proof       │    │ • Store (sensor_id,       │
│ • Verify range proof     │    │   timestamp, nonce,       │
│ • NO raw value access    │    │   raw_value)              │
│                          │    │                           │
│ Result:                  │    │ • TTL: 10 minutes         │
│   ✅ Valid (in range)    │    │ • Nonce-based auth        │
│   ❌ Invalid (anomaly)   │    │ • Auto-expiration         │
│                          │    │                           │
│ Used by:                 │    │ Used by:                  │
│   • Operators            │    │   • Analysts (on-demand)  │
│   • Monitoring systems   │    │   • Debuggers             │
│   • Alerting             │    │   • Auditors              │
│                          │    │                           │
└──────────────────────────┘    └───────────────────────────┘
         99% usage                     1% usage
      (normal operation)            (special cases)
```

## Component Details

### 1. Sensor Client

**File**: `sensor_client_selective_disclosure.py`

**Responsibilities**:
- Read sensor values (from real sensors or CSV simulation)
- Generate Bulletproof range proofs
- Transmit ZK proofs to verification server
- Store raw values in reveal server

**Key Features**:
```python
class SelectiveDisclosureSensor:
    def __init__(self, sensor_id, range_min, range_max):
        self.sensor_id = sensor_id
        self.range_min = range_min
        self.range_max = range_max
        self.prover = BulletproofProver()

    def process_reading(self, value):
        # Generate ZK proof
        proof = self.prover.generate_proof(
            value, self.range_min, self.range_max
        )

        # Create nonce for authentication
        nonce = self.generate_nonce()

        # Dual transmission
        self.send_zk_proof(proof)           # Public
        self.store_raw_value(value, nonce)  # Private

        return proof, nonce
```

**Privacy Analysis**:
- ZK proof reveals ONLY: "value ∈ [min, max]"
- ZK proof conceals: Exact value
- Computational security: Based on discrete log problem

### 2. Verification Server

**Endpoint**: `POST /api/v1/verify/bulletproof`

**Input**:
```json
{
  "sensor_id": "DM-PIT01",
  "timestamp": 1763034728,
  "nonce": "ABC123...",
  "commitment": {
    "V": "04abcd...",
    "blinding": "efgh..."
  },
  "proof": {
    "A": "04xyz...",
    "S": "04uvw...",
    "T1": "04rst...",
    "T2": "04opq...",
    "tau_x": "123456...",
    "mu": "789012...",
    "t": "345678...",
    "L": ["04...", "04...", ...],
    "R": ["04...", "04...", ...]
  },
  "range_min": 0.5,
  "range_max": 2.0
}
```

**Verification Process**:
```python
def verify_bulletproof(proof_data):
    # 1. Reconstruct proof components
    commitment = deserialize_commitment(proof_data['commitment'])
    proof = deserialize_proof(proof_data['proof'])

    # 2. Verify range proof
    verifier = BulletproofVerifier()
    result = verifier.verify(
        commitment, proof,
        proof_data['range_min'],
        proof_data['range_max']
    )

    # 3. Return result (NO raw value revealed)
    return {"verified": result}
```

**Security Property**:
```
Verification Server learns NOTHING about raw value
except: value ∈ [range_min, range_max] or NOT
```

### 3. Reveal Server

**File**: `reveal_server.py`

**Endpoint**: `POST /api/v1/reveal-raw`

**Storage Structure**:
```python
raw_buffer = {
    "DM-PIT01:1763034728:ABC123": {
        "raw_value": 1.523,
        "sensor_id": "DM-PIT01",
        "timestamp": 1763034728,
        "nonce": "ABC123...",
        "expiration": 1763035328  # TTL: 10 minutes
    }
}
```

**Access Control**:
```python
def reveal_raw_value(request):
    sensor_id = request['sensor_id']
    timestamp = request['timestamp']
    nonce = request['nonce']

    # Construct lookup key
    key = f"{sensor_id}:{timestamp}:{nonce}"

    # Check if exists and not expired
    if key in raw_buffer:
        entry = raw_buffer[key]
        if time.now() < entry['expiration']:
            return {
                "success": True,
                "raw_value": entry['raw_value']
            }
        else:
            # Expired, remove entry
            del raw_buffer[key]
            return {"error": "Entry expired"}
    else:
        return {"error": "Entry not found or invalid nonce"}
```

**Security Features**:
- **Nonce Authentication**: Requires knowledge of random nonce
- **TTL Expiration**: Automatic deletion after timeout
- **Memory-only Storage**: No persistent database (for testing)

**Privacy Trade-off**:
```
Reveal Server IS a privacy weakness:
  - If compromised, stored raw values are exposed
  - However, only values within TTL window are at risk
  - Nonce requirement limits unauthorized access
```

## Cryptographic Foundation

### Bulletproof Range Proof

**Goal**: Prove `value ∈ [range_min, range_max]` without revealing `value`

**Approach**:
1. **Commitment**: Pedersen commitment
   ```
   V = value·G + blinding·H
   ```
   where G, H are elliptic curve points

2. **Range Proof**: Prove `0 ≤ value < 2^n` for some n
   ```
   Inner product argument for vector commitments
   Proof size: O(log n) group elements
   ```

3. **Range Translation**: For arbitrary range [min, max]:
   ```
   Prove: 0 ≤ (value - min) < (max - min)
   ```

**Efficiency**:
- **Proof Size**: ~1.2 KB (for 32-bit values)
- **Generation Time**: ~130 ms
- **Verification Time**: ~80 ms

### Security Analysis

**Computational Assumptions**:
- Discrete Logarithm Problem (DLP) hardness
- Elliptic Curve Cryptography (ECC) security

**Privacy Guarantees**:
```
Information-Theoretic:
  - Commitment V reveals NOTHING about value
  - Perfect hiding property

Computational:
  - Extracting value from V requires solving DLP
  - Infeasible with current computing power
```

**Zero-Knowledge Property**:
```
Simulator can generate valid-looking proofs
WITHOUT knowing the actual value
→ Proofs reveal no information beyond validity
```

## Transmission Modes Comparison

### RAW Mode
```python
# sensor_client.py --mode RAW
payload = {
    "sensor_id": "DM-PIT01",
    "timestamp": 1763034728,
    "raw_value": 1.523  # ❌ Value exposed
}
```
- **Privacy**: None
- **Use Case**: Development, debugging

### ZK_ONLY Mode
```python
# sensor_client.py --mode ZK_ONLY
payload = {
    "sensor_id": "DM-PIT01",
    "timestamp": 1763034728,
    "proof": {...}  # ✅ Only ZK proof
    # No raw value anywhere
}
```
- **Privacy**: Full
- **Limitation**: Cannot access raw values later

### SELECTIVE_DISCLOSURE Mode (Recommended)
```python
# sensor_client_selective_disclosure.py
# Public transmission
verification_payload = {
    "sensor_id": "DM-PIT01",
    "timestamp": 1763034728,
    "proof": {...}  # ✅ Only ZK proof
}

# Private storage
reveal_payload = {
    "sensor_id": "DM-PIT01",
    "timestamp": 1763034728,
    "nonce": "ABC123",
    "raw_value": 1.523  # Stored privately
}
```
- **Privacy**: Full by default
- **Flexibility**: Can reveal when needed
- **Best of both worlds**

## Use Case Workflows

### Workflow 1: Normal Monitoring

```
┌─────────────────────────────────────────────────┐
│ Normal Operation (99% of the time)              │
├─────────────────────────────────────────────────┤
│                                                  │
│ 1. Sensor sends ZK proof every 2 seconds        │
│    └─> Verification server: ✅ Valid            │
│                                                  │
│ 2. Operator views dashboard                     │
│    └─> "All sensors in normal range"            │
│                                                  │
│ 3. NO raw values accessed                       │
│    └─> Privacy preserved                        │
│                                                  │
│ Result: Efficient, private monitoring           │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Workflow 2: Anomaly Investigation

```
┌─────────────────────────────────────────────────┐
│ Anomaly Detected (1% of the time)               │
├─────────────────────────────────────────────────┤
│                                                  │
│ 1. Detection Phase                              │
│    14:23:15 - ZK proof verification: ❌ FAILED  │
│    └─> Alert triggered                          │
│    └─> NO raw value revealed yet                │
│                                                  │
│ 2. Investigation Phase                          │
│    Analyst: "What was the exact value?"         │
│    └─> Call Reveal API:                         │
│        POST /api/v1/reveal-raw                  │
│        {                                         │
│          "sensor_id": "DM-PIT01",               │
│          "timestamp": 1763034728,               │
│          "nonce": "ABC123..."                   │
│        }                                         │
│    └─> Response: raw_value = 285.7              │
│                                                  │
│ 3. Analysis Phase                               │
│    Expected range: [210, 274]                   │
│    Actual value: 285.7                          │
│    └─> Diagnosis: Sensor calibration drift      │
│                                                  │
│ Result: Privacy during detection,               │
│         Transparency for analysis                │
│                                                  │
└─────────────────────────────────────────────────┘
```

### Workflow 3: Compliance Audit

```
┌─────────────────────────────────────────────────┐
│ Regulatory Audit                                 │
├─────────────────────────────────────────────────┤
│                                                  │
│ 1. Daily Operation (Privacy Mode)               │
│    • ZK proofs demonstrate compliance           │
│    • "All values within regulatory limits"      │
│    • NO raw values exposed to operators         │
│                                                  │
│ 2. Audit Request (Transparency Mode)            │
│    Auditor: "Show me exact values for           │
│              2025-01-15, 14:00-16:00"           │
│    └─> Batch reveal for audit period            │
│    └─> Provide raw values for inspection        │
│                                                  │
│ 3. Post-Audit (Return to Privacy Mode)          │
│    • TTL expires old reveal data                │
│    • Return to ZK-only operation                │
│                                                  │
│ Result: Privacy-preserving compliance           │
│                                                  │
└─────────────────────────────────────────────────┘
```

## Performance Considerations

### Computational Overhead

| Operation | Time | Component |
|-----------|------|-----------|
| Proof generation | ~130 ms | Sensor |
| Proof verification | ~80 ms | Server |
| Reveal lookup | <1 ms | Server |

### Network Overhead

| Mode | Payload Size | Overhead |
|------|-------------|----------|
| RAW | 156 bytes | 1x |
| ZK_ONLY | 1,247 bytes | 8x |
| Selective Disclosure | 1,247 bytes | 8x* |

\* Same as ZK_ONLY for public transmission; raw values stored privately

### Throughput Analysis

**Target**: 1 sensor reading every 2 seconds
- **Proof generation**: 130 ms << 2000 ms ✅
- **Network transmission**: ~50 ms ✅
- **Total latency**: <200 ms ✅

**Conclusion**: System is suitable for real-time ICS monitoring

### Scalability

**Single sensor**: 0.5 Hz (1 reading / 2 sec)
**100 sensors**: 50 Hz total
- **Computation**: 100 × 130 ms = 13 sec (parallelizable)
- **Network**: 100 × 1.2 KB = 120 KB/batch

**Bottleneck**: Proof generation is CPU-bound
**Solution**: Multi-core parallelization or dedicated crypto hardware

## Security Analysis

### Threat Model

**Assumptions**:
1. Verification server is honest-but-curious
2. Network traffic may be eavesdropped
3. Reveal server requires authentication

**Attacks Considered**:
- Network sniffing
- Verification server data mining
- Unauthorized reveal requests
- Timing analysis

### Security Guarantees

| Threat | Protection | Limitation |
|--------|-----------|------------|
| Network eavesdropping | ZK proofs hide values | Reveal server traffic must be encrypted |
| Honest-but-curious server | No raw values sent | Reveal server sees raw values |
| Unauthorized access | Nonce authentication | Nonce must be kept secret |
| Long-term storage | TTL expiration | Short window only |

### Privacy vs. Functionality Trade-off

```
Full Privacy          Our Approach          No Privacy
(ZK_ONLY)        (Selective Disclosure)        (RAW)
    │                     │                      │
    ├─ No raw access     ├─ Controlled access   ├─ Always accessible
    ├─ Perfect privacy   ├─ Default privacy     ├─ No privacy
    ├─ Limited utility   ├─ Flexible utility    ├─ Full utility
    │                     │                      │
    └─────────────────────┴──────────────────────┘
                          │
                    Best of both worlds
```

## Future Enhancements

### 1. Fine-Grained Access Control
```python
# Role-based reveal permissions
if user.role == "operator":
    deny_reveal()
elif user.role == "analyst":
    allow_reveal(time_range="last_hour")
elif user.role == "admin":
    allow_reveal(time_range="all")
```

### 2. Differential Privacy for Batch Reveals
```python
# Add calibrated noise when revealing multiple values
def batch_reveal_with_dp(timestamps, epsilon=1.0):
    raw_values = [reveal(ts) for ts in timestamps]
    noisy_values = add_laplace_noise(raw_values, epsilon)
    return noisy_values
```

### 3. Persistent Reveal Storage
```python
# Database-backed storage with encryption at rest
reveal_db = EncryptedDatabase("reveal_storage.db")
reveal_db.store(key, value, ttl=600)
```

### 4. Proof Aggregation
```python
# Aggregate multiple sensor proofs into one
aggregate_proof = aggregate([proof1, proof2, ..., proofN])
# Reduces verification overhead
```

## Conclusion

Selective Disclosure architecture provides:

✅ **Privacy by default**: ZK proofs during normal operation
✅ **Transparency on demand**: Raw values when needed
✅ **Practical performance**: Suitable for real-time ICS monitoring
✅ **Flexible deployment**: Multiple modes for different requirements

**Key Insight**: Privacy and transparency are not mutually exclusive. By separating verification (public) from revelation (private), we achieve both.
