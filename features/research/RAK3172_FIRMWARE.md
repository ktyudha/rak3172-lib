# RAK3172 Firmware: Alice, Bob, Eve

Jika ketiga device menggunakan **RAK3172** (Python yang sudah ada + 2 sketch Arduino RUI3 tambahan).

---

## Setup: 3x RAK3172 modules

| Device | Role | Upload | Deploy |
|---|---|---|---|
| Alice | Node (sender) | `alice_rak3172.ino` | Arduino IDE → RAK3172 |
| Bob | Gateway (receiver + reply) | `bob_rak3172.ino` | Arduino IDE → RAK3172 |
| Eve | Listener (receive only) | `eve_rak3172.ino` | Arduino IDE → RAK3172 |

**Atau mix dengan Python:**
- Bob: `python features/bob.py` (RAK3172 + RUI3 library)
- Eve: `python features/eve.py` (RAK3172 + RUI3 library)
- Alice: `alice_rak3172.ino` (Arduino IDE)

---

## Skematis: Semua RAK3172

```
Alice (RAK3172) ←─→ Bob (RAK3172)
                    ↑
                  Eve (RAK3172) listen saja
```

**Alice:**
- Send ping "N;" to Bob
- Wait for pong "N;-XX" from Bob
- Measure RSSI of pong
- Repeat

**Bob:**
- Listen for ping from Alice
- Measure RSSI of ping
- Wait 100 ms
- Send pong with measured RSSI
- Repeat

**Eve:**
- Listen for ALL frames (ping & pong)
- Measure RSSI of each
- Log dengan format: `[eve] from -> to type #seq: rssi=X snr=Y`
- Never send

---

## File yang dibuat

### Arduino sketches (RUI3 firmware API)

1. **`alice_rak3172.ino`** — Alice (sender)
   - Send ping every 1 second
   - Wait for pong from Bob
   - Measure RSSI of pong
   - Similar to Python alice.py but in C++/RUI3

2. **`bob_rak3172.ino`** — Bob (gateway)
   - Listen for ping from Alice
   - Measure RSSI of ping
   - Send pong with RSSI after 100 ms delay
   - Similar to Python bob.py but in C++/RUI3

3. **`eve_rak3172.ino`** — Eve (listener)
   - Listen for all frames
   - Never send
   - Measure RSSI & SNR
   - Log: `[eve] alice -> bob ping #N: rssi=X snr=Y`

### Existing Python (already available)

- **`features/bob.py`** — Can use instead of bob_rak3172.ino
- **`features/eve.py`** — Can use instead of eve_rak3172.ino

---

## Setup & Upload

### Hardware preparation

Siapkan 3x RAK3172 module (dengan antenna + power).

### Radio config (semua harus SAMA)

Edit di `.ino` files:
```cpp
double myFreq = 868000000;  // 868 MHz
uint16_t sf = 7;            // SF7
uint16_t bw = 125E3;        // 125 kHz
uint16_t cr = 5;            // CR 4/5
uint16_t preamble = 8;      // Preamble 8
```

### Upload sketches ke RAK3172

Untuk setiap device:
1. **Arduino IDE** → Open file (alice_rak3172.ino / bob_rak3172.ino / eve_rak3172.ino)
2. **Tools** → Board: `RAK3172`
3. **Tools** → Port: Select COM port
4. **Upload** (Sketch → Upload atau Ctrl+U)
5. **Serial Monitor** (115200 baud) untuk lihat output

---

## Expected output

### Alice terminal
```
[alice] LoRa initialized OK
[alice] sent ping #1
[alice] pong #1: rssi_at_bob=-71 rssi_at_alice=-65
[alice] sent ping #2
[alice] pong #2: rssi_at_bob=-69 rssi_at_alice=-63
```

### Bob terminal
```
[bob] LoRa initialized OK, listening...
[bob] ping #1 from 2: rssi=-71 snr=7
[bob] ping #2 from 2: rssi=-69 snr=6
```

### Eve terminal
```
[eve] LoRa initialized OK, listening...
[eve] alice -> bob ping #1: rssi=-71 snr=7
[eve] bob -> alice pong #1: rssi=-65 snr=7
[eve] alice -> bob ping #2: rssi=-69 snr=6
[eve] bob -> alice pong #2: rssi=-63 snr=6
```

---

## Payload & Frame format

**Same as Python version:**

| Data | Ping | Pong | Example |
|---|---|---|---|
| **Format** | `<seq>;` | `<seq>;<rssi>` | `1;` vs `1;-71` |
| **Frame** | `[2][1]1;` | `[1][2]1;-71` | [from][to][payload] |

**RSSI measurement:**
- Ping: Bob measures RSSI when receive → echo back in pong
- Pong: Alice measures RSSI when receive → log
- Eve: Measures RSSI of both ping & pong independently

---

## RUI3 API callback model

Semua sketch menggunakan **callback-based** RX:

```cpp
void recv_cb(rui_lora_p2p_recv_t data) {
    // data.Buffer = frame bytes
    // data.BufferSize = frame length
    // data.Rssi = received signal strength
    // data.Snr = signal-to-noise ratio
}

api.lora.registerPRecvCallback(recv_cb);
api.lora.precv(65534);  // Start listening (continuous RX)
```

Berbeda dengan Python yang pakai `on_receive` callback di library layer.

---

## Differences: Arduino RUI3 vs Python

| Aspek | Python (bob.py, eve.py) | Arduino RUI3 (sketches) |
|---|---|---|
| **API** | LoRaP2P library wrapper | RUI3 API direct |
| **Frame parsing** | Library auto-parse | Manual: `Buffer[0]`, `Buffer[1]`, `Buffer+2` |
| **Callback** | Handler class + threading | Direct callback function |
| **RSSI** | String from callback → float | int16_t direct from data.Rssi |
| **Threading** | Bob pakai thread untuk reply | Arduino single-threaded, blocking delay |
| **Deploy** | `python features/bob.py` | Arduino IDE upload |

**Both produce identical output format.**

---

## Configuration options

### Tweak delay di Bob

Edit di `bob_rak3172.ino`:
```cpp
#define REPLY_DELAY_MS 100  // Default 100 ms

// Di recv_cb():
delay(REPLY_DELAY_MS);  // Then send pong
```

### Tweak timeout di Alice

Edit di `alice_rak3172.ino`:
```cpp
#define PONG_TIMEOUT_MS 5000  // Default 5 seconds
```

### Tweak radio config

Edit di semua sketch:
```cpp
double myFreq = 868000000;
uint16_t sf = 7;
```

---

## Debugging

### Frame tidak diterima sama sekali
- Cek radio config: frequency, SF, BW, CR, preamble SAMA di semua 3
- Cek antenna terpasang
- Cek power supply

### RSSI nilai aneh (0 atau -200)
- Normal saja, tergantung posisi dan RF environment
- Bandingkan consistency antar device

### Alice tidak dapat pong dari Bob
- Cek Bob sedang listen?
- Cek address: Alice kirim ke 1, Bob listen ke address 1?
- Check serial monitor Bob → harus print "[bob] ping #N from 2"

### Eve tidak dapat frame
- Cek Eve sedang listen? Serial monitor harus print "listening..."
- Cek Eve address tidak sama dengan Alice/Bob (conflict)
- Cek radio config match

---

## Advantages: All Arduino RUI3

✅ **Consistent firmware** — Semua device gunakan Arduino IDE  
✅ **Easier deployment** — Upload 3x sketches, done  
✅ **Same behavior** — Output format identical  
❌ **More sketches** — 3 file untuk 3 device (vs 2 Python + 1 sketch jika mix)

---

## Hybrid: Some Python, some Arduino

**Recommended for flexibility:**

| Device | Implementation | Advantages |
|---|---|---|
| Alice | Arduino RUI3 sketch | Easy to tweak timing locally |
| Bob | Python + RAK3172 library | Full LoRaWAN potential, better logging |
| Eve | Python + RAK3172 library | Easy to integrate with data collection |

See [CROSS_PLATFORM.md](CROSS_PLATFORM.md) for ESP32 + RFM95 Alice variant.

---

## Next steps

1. **Prepare hardware:** 3x RAK3172 + antenna + power
2. **Edit .ino files:** Verify radio config matches
3. **Upload:** Bob → Alice → Eve (order doesn't matter, but Eve first if want to log everything)
4. **Monitor:** Open 3 Serial Monitor windows (115200 baud)
5. **Analyze:** Collect RSSI data, compare Eve perspective vs Alice/Bob
