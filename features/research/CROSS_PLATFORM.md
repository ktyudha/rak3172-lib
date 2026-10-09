# Cross-platform: ESP32 + RAK3172

**Skenario:** Alice gunakan ESP32 + RFM95 (Arduino), Bob & Eve tetap RAK3172 (Python).

Ini **possible** karena payload & frame format yang sama. Tidak perlu ubah Bob/Eve.

---

## ✅ Yang tetap SAMA

| Aspek | Detail |
|---|---|
| **Payload format** | `"<seq>;<rssi>"` — identik di ESP32 & RAK3172 |
| **Frame header** | `[from_addr:1][to_addr:1][payload:N]` — sama persis |
| **Radio config** | Frequency, SF, BW, CR, Preamble — harus identik |
| **Addressing** | Alice=2, Bob=1, Eve=3 — bisa tetap sama |

---

## ⚠️ Yang BERUBAH

| Aspek | Python Alice (RAK3172) | C++ Alice (ESP32 + RFM95) |
|---|---|---|
| **Entry point** | `features/alice.py` | `features/alice_esp32.ino` |
| **RSSI measurement** | `rssi` dari parameter `on_payload()` | `LoRa.packetRssi()` setelah `LoRa.parsePacket()` |
| **Timing** | Python threads + `Event` | Arduino blocking loop / interrupt |
| **Build & deploy** | `python features/alice.py` | Arduino IDE upload ke ESP32 |

---

## 🔌 Wiring: ESP32 + RFM95

```
RFM95 Pin    →    ESP32 GPIO
───────────────────────────
NSS (CS)     →    GPIO 5
RST          →    GPIO 14
DIO0         →    GPIO 2
MOSI         →    GPIO 23 (SPI default)
MISO         →    GPIO 19 (SPI default)
SCK          →    GPIO 18 (SPI default)
GND          →    GND
3.3V         →    3.3V
```

---

## 🎛️ Radio config: MUST MATCH

**ESP32 sketch (alice_esp32.ino):**
```cpp
#define FREQUENCY 868E6       // 868 MHz
#define SPREADING_FACTOR 7    // SF7
#define BANDWIDTH 125E3       // 125 kHz
#define CODING_RATE 5         // CR 4/5
#define PREAMBLE_LEN 8        // Preamble 8
LoRa.setSyncWord(0x12);       // Sync word
```

**Bob (RAK3172, .env):**
```
LORA_FREQUENCY=868000000      # CHANGE from 915000000!
LORA_SPREADING_FACTOR=7
LORA_BANDWIDTH=0              # = 125 kHz for SF7
LORA_CODING_RATE=0            # = CR 4/5
LORA_PREAMBLE=8
```

**Eve (.env):** Same as Bob.

⚠️ **Critical:** Frequency, SF, BW, CR, Preamble, Sync word MUST be **identical**.

---

## 🚀 Setup flow

### 1. Hardware setup

**Bob (RAK3172):**
```
Raspberry Pi ↔ RAK3172 (serial port /dev/ttyUSB0)
```

**Eve (RAK3172):**
```
Raspberry Pi ↔ RAK3172 (serial port /dev/ttyUSB0)
```

**Alice (ESP32 + RFM95):**
```
ESP32 ↔ RFM95 (SPI via GPIO 5,14,2,23,19,18)
```

### 2. Configure

**Bob (.env):**
```
LORA_MODE=p2p
LORA_ROLE=gateway
LORA_ADDRESS=1
LORA_FREQUENCY=868000000      # ← CHANGE
LORA_SERIAL_PORT=/dev/ttyUSB0
LORA_SPREADING_FACTOR=7
LORA_BANDWIDTH=0
LORA_CODING_RATE=0
LORA_PREAMBLE=8
```

**Eve (.env):** Same as Bob.

**Alice (alice_esp32.ino):**
```cpp
#define ALICE_ADDRESS 2
#define BOB_ADDRESS 1
#define FREQUENCY 868E6
#define SPREADING_FACTOR 7
// ... (check all define match with Bob/Eve)
```

### 3. Upload & startup

```bash
# Terminal 1: Bob (gateway)
LORA_ADDRESS=1 python features/bob.py

# Terminal 2: Eve (listener)
LORA_ADDRESS=3 python features/eve.py

# Device 3: Alice (ESP32)
# - Open arduino_ide/alice_esp32.ino
# - Select Board: ESP32 Dev Module
# - Select COM port
# - Upload
# - Open Serial Monitor (115200 baud) to see output
```

### 4. Monitor output

**Bob terminal:**
```
[bob] ping #1 from 2: rssi=-70 snr=7
[bob] ping #2 from 2: rssi=-68 snr=6
```

**Eve terminal:**
```
[eve] alice -> bob ping #1: rssi=-70 snr=7
[eve] bob -> alice pong #1: rssi=-65 snr=7
```

**ESP32 Serial Monitor:**
```
[alice] sent ping #1
[alice] pong #1: rssi_at_bob=-70 rssi_at_alice=-65
```

---

## 📊 Differences: Arduino vs Python implementation

### Payload parsing

**Python (Bob/Eve):**
```python
from features.research.payloads import Probe
probe = Probe.from_payload(b"5;-71")  # → Probe(seq=5, rssi=-71.0)
```

**Arduino (Alice):**
```cpp
String payload = "5;-71";
int semicolon_pos = payload.indexOf(';');
int seq = payload.substring(0, semicolon_pos).toInt();
float rssi_val = payload.substring(semicolon_pos + 1).toFloat();
```

✅ Both decode the same format.

### RSSI measurement

**Python (on_payload callback):**
```python
def on_payload(self, from_addr, message, rssi, snr):
    # rssi is string from library, converted to float
    self.rssi_at_alice = float(rssi)  # e.g., "-65"
```

**Arduino (after parse):**
```cpp
int packet_size = LoRa.parsePacket();
if (packet_size) {
    // ... read frame
    rssi_at_alice = LoRa.packetRssi();  // e.g., -65 (int)
}
```

✅ Same measurement, different API.

### Threading

**Python (sync between RX thread & sender loop):**
```python
handler = AliceHandler()  # Has threading.Event
handler.expect(seq)
node.send_to_gateway(ping_bytes)
handler.wait_pong(timeout=5.0)  # Block with timeout
```

**Arduino (single loop, polling):**
```cpp
void loop() {
  packet_size = LoRa.parsePacket();
  if (packet_size) handle_receive();
  // ...
  wait_for_pong(5000);  // Poll-based timeout
}
```

✅ Different models, same timing semantics.

---

## 🔍 Debugging

### Alice (ESP32) can't send

- Serial Monitor showing error? Check wiring GPIO 5, 14, 2, 23, 19, 18.
- LoRa.begin() failed? Check if RFM95 power is OK.
- Check frequency match with Bob/Eve (868 MHz).

### Bob/Eve can't receive ping from Alice

- Check radio config matches:
  - Frequency: 868 MHz on all three
  - SF, BW, CR, Preamble, Sync word
- Check Bob `.env` correctly set to gateway mode.
- Check if Alice `ALICE_ADDRESS=2` is correct.

### Alice received pong but RSSI is -0 or strange

- Check if Bob is actually sending pong (should see it in Eve terminal).
- ESP32 `LoRa.packetRssi()` might return different value than RAK3172.
- Difference is normal (different RF front-end), as long as it's consistent.

### Sync word mismatch

If Alice receives frames but can't decode:
- ESP32 default sync word: 0x34 (LoRaWAN)
- RAK3172 default: likely 0x34 too
- If different, explicitly set both to same value (e.g., 0x12)

```cpp
// In alice_esp32.ino
LoRa.setSyncWord(0x12);  // Match with Bob/Eve
```

---

## ✨ Benefits

- **Payload unchanged** → No code change in Bob/Eve
- **Same protocol** → Easy to mix hardware
- **Modular** → Can replace any part (ESP32 Alice → RAK3172 Alice, etc.)

---

## 📝 Notes

1. **RSSI difference:** ESP32 RFM95 and RAK3172 RF performance differ. Small RSSI offset is normal.
2. **Timing:** Arduino loop is tighter; Python might have more jitter. Should not affect ping/pong protocol.
3. **Scalability:** Can use this pattern to add more ESP32 nodes or other LoRa hardware, as long as frame format & radio config match.

---

## 📂 Files

- `alice_esp32.ino` — Arduino sketch for ESP32 + RFM95 (replaces Python alice.py for this device only)
- `bob.py` — No change (still RAK3172 Python)
- `eve.py` — No change (still RAK3172 Python)
- `research/payloads/probe.py` — No change (used by Bob/Eve, not Alice)
- `research/handlers/bob_handler.py` — No change (still RAK3172 Python)
- `research/handlers/eve_handler.py` — No change (still RAK3172 Python)
