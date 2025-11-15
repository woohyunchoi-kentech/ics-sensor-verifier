# ICS Sensor Verifier: Privacy by Default, Transparency on Demand

Privacy-preserving sensor monitoring for Industrial Control Systems using Bulletproof range proofs with selective disclosure architecture.

## Core Philosophy

**Zero-knowledge proofs are sufficient for most scenarios. But when you need raw values, you can access them.**

Traditional privacy systems force a binary choice:
- Full privacy (no raw access) OR
- No privacy (full transparency)

Our system provides both:
- **Default**: ZK proofs protect sensor values during normal operation
- **On-demand**: Authorized access to raw values when detailed analysis is needed

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    Sensor Device                         │
├──────────────────────────────────────────────────────────┤
│  1. Read sensor value                                    │
│  2. Generate Bulletproof range proof                     │
│  3. Send ZK proof → Verification Server                  │
│  4. Store RAW value → Reveal Server (TTL: 10 min)        │
└──────────────────────────────────────────────────────────┘
                     ↓                    ↓
         ┌─────────────────┐    ┌─────────────────┐
         │ Verification    │    │ Reveal Server   │
         │ Server          │    │ (Optional)      │
         ├─────────────────┤    ├─────────────────┤
         │ Verify ZK proof │    │ Store RAW values│
         │ ✅ In range?    │    │ with TTL        │
         │                 │    │                 │
         │ No raw value    │    │ Nonce-based     │
         │ exposure        │    │ authentication  │
         └─────────────────┘    └─────────────────┘
```

## Key Features

### 1. Zero-Knowledge Range Proofs
- **Bulletproof** implementation for efficient range proofs
- Prove sensor value is within valid range WITHOUT revealing the value
- Small proof size: O(log n) complexity

### 2. Multiple Transmission Modes

| Mode | Privacy | Raw Access | Use Case |
|------|---------|------------|----------|
| `RAW` | None | Always | Development, debugging |
| `ZK_ONLY` | Full | Never | High privacy requirements |
| `HYBRID` | Partial | Always | Compliance scenarios |
| `SELECTIVE_DISCLOSURE` | Full* | On-demand | **Recommended** |

\* Full privacy by default, controlled access when needed

### 3. Selective Disclosure Benefits

**Most of the time**: ZK proof is sufficient
```python
# Normal monitoring - no raw value needed
✅ "Is the temperature in normal range?" → ZK proof
✅ "Did any anomaly occur?" → ZK proof failed
✅ "Compliance verification" → ZK proof
```

**When you need details**: Access raw values
```python
# Detailed analysis - reveal raw values
🔍 "What was the exact temperature?" → Reveal API
🔍 "Root cause analysis" → Reveal API
🔍 "Model training" → Reveal API
```

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/woohyunchoi-kentech/ics-sensor-verifier.git
cd ics-sensor-verifier

# Install dependencies
pip3 install petlib flask requests
```

### 1. Start Reveal Server (Optional but Recommended)

```bash
python3 reveal_server.py --port 9000 --host 127.0.0.1 --ttl 600
```

- Stores raw values with 10-minute TTL
- Provides REST API for selective reveal
- Nonce-based authentication

### 2. Run Sensor Client

**Selective Disclosure Mode** (Recommended):
```bash
python3 sensor_client_selective_disclosure.py \
  --server http://VERIFIER_IP:8085 \
  --sensor DM-PIT01 \
  --csv your_sensor_data.csv \
  --range-min 0.5 \
  --range-max 2.0 \
  --interval 2.0 \
  --reveal-url http://127.0.0.1:9000
```

**Other Modes**:
```bash
# RAW mode (no privacy)
python3 sensor_client.py --mode RAW --server http://VERIFIER_IP:8085

# ZK_ONLY mode (full privacy, no reveal)
python3 sensor_client.py --mode ZK_ONLY --server http://VERIFIER_IP:8085
```

### 3. Access Raw Values When Needed

```bash
# Reveal a specific sensor reading
curl -X POST http://localhost:9000/api/v1/reveal-raw \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_id": "DM-PIT01",
    "event_ts": 1763034728,
    "nonce": "ABC123..."
  }'

# Response
{
  "success": true,
  "raw_value": 1.234567,
  "sensor_id": "DM-PIT01",
  "timestamp": 1763034728
}
```

## Use Cases

### Scenario 1: Normal Operation
**Goal**: Continuous monitoring of sensor values

**Solution**: ZK proofs are sufficient
- Sensor sends range proofs every 2 seconds
- Verification server validates: "Value in [min, max]?"
- ✅ No raw value exposure
- ✅ Privacy preserved

### Scenario 2: Anomaly Investigation
**Goal**: Understand why alarm triggered

**Workflow**:
1. **Detection** (ZK proof): Alarm triggered at 14:23:15
2. **Investigation** (Reveal API): "What was the exact value?"
3. **Analysis**: Raw value = 285.7 (expected: 210-274)
4. **Diagnosis**: Sensor calibration drift detected

### Scenario 3: Regulatory Audit
**Goal**: Prove compliance while maintaining privacy

**Solution**:
- **Daily operation**: ZK proofs demonstrate range compliance
- **Audit request**: Selectively reveal specific readings
- **Benefit**: Privacy for normal operation, transparency for audit

## Project Structure

```
ics-sensor-verifier/
├── README.md                                   # This file
├── sensor_client.py                           # Multi-mode sensor client
├── sensor_client_selective_disclosure.py      # Selective disclosure client
├── reveal_server.py                           # RAW value storage server
├── crypto/
│   ├── __init__.py
│   └── bulletproof_prover_production.py       # Bulletproof implementation
└── docs/
    ├── ARCHITECTURE.md                        # Detailed architecture
    ├── USAGE.md                              # Usage examples
    └── PAPER_OUTLINE.md                      # Research paper outline
```

## Performance

Based on testing with HAI dataset (real ICS sensor data):

| Metric | Value | Note |
|--------|-------|------|
| Proof generation | ~130 ms | Per sensor reading |
| Payload overhead | ~8x | vs RAW (1.2 KB vs 156 bytes) |
| Latency | < 200 ms | End-to-end |
| Throughput | 7-8 readings/sec | Per sensor |

**Conclusion**: Suitable for real-time ICS monitoring (typical interval: 1-10 seconds)

## Comparison with Other Approaches

| Approach | Privacy | Raw Access | Accuracy | Overhead |
|----------|---------|------------|----------|----------|
| RAW transmission | ❌ None | ✅ Always | ✅ 100% | ✅ 1x |
| Homomorphic Enc. | ✅ Full | ❌ Never | ✅ 100% | ❌ 100x+ |
| Differential Privacy | ⚠️ Statistical | ❌ Never | ❌ ~95% | ✅ 1x |
| Traditional ZKP | ✅ Full | ❌ Never | ✅ 100% | ⚠️ 8x |
| **Our Approach** | ✅ Full | ✅ On-demand | ✅ 100% | ⚠️ 8x |

**Key Advantage**: Best of both worlds - privacy without sacrificing future access.

## Security Model

### Privacy Guarantees
- **ZK proofs**: Computationally infeasible to extract raw values
- **Reveal server**: Access controlled by nonce authentication
- **TTL expiration**: Automatic deletion after timeout (default: 10 minutes)

### Threat Model
- Honest-but-curious verification server
- Network eavesdropping
- Unauthorized reveal requests

### Limitations
- Reveal server compromise exposes stored raw values
- Timing attacks may infer value ranges
- Requires trusted reveal server deployment

## Dataset

Tested with **HAI (Hardware-in-the-loop Augmented ICS)** dataset:
- Real industrial control system sensor data
- Sensors: DM-PIT01, DM-FT03, P1_PIT01, etc.
- Normal and anomaly scenarios included

## Related Projects

- **Verification Server**: [ics-sensor-verifier](https://github.com/woohyunchoi-kentech/ics-sensor-verifier)
- **Sensor Client**: [pcbp](https://github.com/woohyunchoi-kentech/pcbp) (this project)

## License

This project is for research and educational purposes.

## Citation

If you use this code in your research, please cite:

```bibtex
@misc{ics-sensor-verifier,
  title={Privacy-Preserving ICS Sensor Monitoring with Selective Disclosure},
  author={Woohyun Choi},
  year={2025},
  howpublished={\url{https://github.com/woohyunchoi-kentech/ics-sensor-verifier}}
}
```

## Contact

For questions or issues, please open a GitHub issue.

---

**Remember**: Zero-knowledge proofs are sufficient for most scenarios. But when you need raw values, you can access them. This is the power of selective disclosure.
