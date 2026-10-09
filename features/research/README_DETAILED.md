# Research: Alice, Bob, Eve

RSSI measurement experiment antara tiga RAK3172 module (P2P, radio setting sama untuk semua).

## Skenario

```
Alice --ping #N--> Bob        Bob measure RSSI dari Alice
Alice <--pong #N-- Bob        Bob tunggu 100 ms, balas carry RSSI-nya
(repeat)                      Eve dengarkan kedua-duanya, catat RSSI masing-masing
```

## Setup: 3 device

| Device | Peran | `LORA_ADDRESS` | `LORA_GATEWAY_ADDRESS` | Jalankan |
|---|---|---|---|---|
| **Bob** | Gateway (penerima) | 1 | — | `python features/bob.py` |
| **Alice** | Node (pengirim) | 2 | 1 | `python features/alice.py` |
| **Eve** | Listener (hanya dengar) | 3 | — | `python features/eve.py` |

**Urutan startup:** Mulai Bob dan Eve terlebih dahulu, lalu Alice. Alice menunggu pong hingga 5 detik sebelum kirim ping berikutnya.

---

## Struktur folder

```
features/research/
  ├─ payloads/
  │  ├─ probe.py               Probe: kontrak pesan ("<seq>;<rssi>")
  │  └─ README.md              Penjelasan class Probe, metode, format, tweak
  │
  ├─ handlers/
  │  ├─ alice_handler.py       AliceHandler: terima pong, ukur RSSI
  │  ├─ bob_handler.py         BobHandler: terima ping, balas pong + RSSI
  │  ├─ eve_handler.py         EveHandler: dengarkan semua, log saja
  │  └─ README.md              Penjelasan tiap handler, method, tweak, flow
  │
  └─ __init__.py

features/
  ├─ bob.py                    Entry point Bob (wiring saja)
  ├─ alice.py                  Entry point Alice (loop send + wait pong)
  ├─ eve.py                    Entry point Eve (start listener)
  └─ README.md                 (file ini)
```

---

## Penjelasan file

### Entry Points

| File | Apa | Jalankan di device mana |
|---|---|---|
| **bob.py** | Gateway: build `P2PGateway` dengan `BobHandler`, loop forever | Raspberry Pi/Linux dengan RAK3172 address 1 |
| **alice.py** | Node: build `P2PNode` dengan `AliceHandler`, loop kirim ping & tunggu pong | Raspberry Pi/Linux dengan RAK3172 address 2 |
| **eve.py** | Listener: build `LoRaP2P` dengan `EveHandler`, loop forever | Raspberry Pi/Linux dengan RAK3172 address 3 |

**Kesamaan:** Semuanya memakai `.env` dengan `LORA_*` variable. Baca dari environment saat startup (`*.from_env()`).

**Perbedaan:**
- Bob pakai `P2PGateway` (gateway role, filter frame ke address diri)
- Alice pakai `P2PNode` (node role, kirim ke gateway, terima command)
- Eve pakai bare `LoRaP2P` (dengarkan semua, tidak ada filter)

---

### Payloads: `research/payloads/probe.py`

**Apa:** Kontrak pesan antara Alice ↔ Bob.

**Format:** `"<seq>;<rssi>"` misal `"5;"` (ping) atau `"5;-71"` (pong).

**Class: `Probe`**
```python
@dataclass
class Probe(Payload):
    seq: int                      # Nomor urut (1, 2, 3, ...)
    rssi: Optional[float] = None  # RSSI yang diukur (kosong untuk ping, terisi untuk pong)
```

**Metode:**
- `to_payload() -> bytes` — Encode untuk kirim
- `from_payload(bytes) -> Optional[Probe]` — Decode saat terima (return None jika malformed)

**Detail:** Lihat [research/payloads/README.md](research/payloads/README.md)

---

### Handlers: `research/handlers/`

**Apa:** Kelas yang react saat frame diterima.

**AliceHandler** (node side)
- Terima pong dari Bob
- Ukur RSSI pong
- Simpan RSSI yang Bob ukur (dari payload)
- Bangunkan sender loop

**BobHandler** (gateway side)
- Terima ping dari Alice
- Ukur RSSI ping
- Tunggu 100 ms (configurable)
- Balas pong carry RSSI Bob

**EveHandler** (listener side)
- Terima SETIAP frame (no filter)
- Parse Probe payload
- Log dengan label alamat pengirim/tujuan

**Detail:** Lihat [research/handlers/README.md](research/handlers/README.md)

---

## Alur kerja

### Fase 1: Setup
1. Set `.env` di tiap device:
   ```
   # Bob
   LORA_ADDRESS=1
   LORA_MODE=p2p
   LORA_ROLE=gateway
   LORA_SERIAL_PORT=/dev/ttyUSB0

   # Alice
   LORA_ADDRESS=2
   LORA_GATEWAY_ADDRESS=1
   LORA_MODE=p2p
   LORA_ROLE=node
   LORA_SERIAL_PORT=/dev/ttyUSB0

   # Eve
   LORA_ADDRESS=3
   LORA_MODE=p2p
   LORA_ROLE=gateway  # or node, tidak penting (tidak kirim)
   LORA_SERIAL_PORT=/dev/ttyUSB0
   ```

2. Pastikan radio setting sama di semua (frequency, spreading factor, dll).

### Fase 2: Startup (urutan penting!)
```bash
# Terminal 1 (Bob)
python features/bob.py
# Output: [bob] listening...

# Terminal 2 (Eve)
python features/eve.py
# Output: [eve] listening...

# Terminal 3 (Alice) — jangan mulai sampai Bob & Eve siap!
python features/alice.py
# Output: [alice] pong #1: rssi_at_bob=... rssi_at_alice=...
```

### Fase 3: Capture data
```
[bob] ping #1 from 2: rssi=-70 snr=7
[eve] alice -> bob ping #1: rssi=-70 snr=7
[eve] bob -> alice pong #1: rssi=-65 snr=7
[alice] pong #1: rssi_at_bob=-70 rssi_at_alice=-65 snr=7
```

Alice & Bob pakai `Probe` class yang sama → protocol tetap konsisten, tidak ada mis-decode.

---

## Catatan penting

1. **Belum ditest di hardware RAK3172 asli.** Hanya cek encode/decode, import, compile.

2. **Delay 100 ms adalah target saja.** Re-arm RX setelah receive ambil ~1 detik, jadi round time asli lebih lama.

3. **Eve tidak punya `reply()`.** Dia listener saja, tidak bisa kirim. Pakai `LoRaP2P` langsung, bukan role gateway/node.

4. **Thread safety:** 
   - Bob pakai thread terpisah untuk `reply()` (tidak dari RX thread, supaya tidak deadlock)
   - Alice pakai `threading.Event` untuk sync antara RX thread dan sender loop

5. **Payload immutable:** Jangan ubah struct `Probe` di production — semua device harus paham format yang sama.

---

## Tweaking

### Ubah delay Bob
Edit `features/bob.py`:
```python
BobHandler(reply_delay=0.05)  # 50 ms
BobHandler(reply_delay=0.2)   # 200 ms
```

### Ubah timeout Alice
Edit `features/alice.py`:
```python
PONG_TIMEOUT = 10.0  # 10 detik (default 5)
```

### Ubah interval ping
Edit `features/alice.py`:
```python
ROUND_DELAY = 0.5  # jeda 500 ms antara pong & ping berikutnya
```

### Ubah format Probe
Edit `research/payloads/probe.py`:
```python
# Misal add checksum / version field
# TAPI ini breaking change → semua device harus update!
```

---

## Debugging

### Bob tidak dapat ping
- Cek `.env` → alamat Bob adalah 1? Alice gateway_address adalah 1?
- Cek radio setting (frequency, SF, BW) sama di semua?
- Cek serial port terbuka?

### Alice tidak dapat pong
- Cek `.env` → Alice address 2, gateway_address 1?
- Cek Bob jalan? Print "[bob] ping #N" muncul?
- Cek timeout (`PONG_TIMEOUT`) cukup lama? (minimal 2-3 detik per round karena RX re-arm)

### Eve tidak dapat frame
- Cek Eve address bukan 1 atau 2 (jangan bentrok)
- Cek radio setting sama
- Eve pakai `LoRaP2P` bare, tidak role gateway/node (biar tidak filter)

---

## Lanjut: Analisis data

Output dari ketiga device:
```
[bob] ping #N: rssi=X snr=Y
[eve] alice -> bob ping #N: rssi=X snr=Y
[eve] bob -> alice pong #N: rssi=Z snr=Y
[alice] pong #N: rssi_at_bob=X rssi_at_alice=Z snr=Y
```

Analisis:
- **rssi_at_bob (X)** — RSSI yang Bob ukur saat terima ping dari Alice
- **rssi_at_alice (Z)** — RSSI yang Alice ukur saat terima pong dari Bob
- **Eve's measurement** — RSSI yang Eve ukur saat dengar setiap frame
  - Eve saat dengar ping = rssi_at_bob (seharusnya sama, asalkan Eve-Bob-Alice posisi tetap)
  - Eve saat dengar pong = rssi_at_alice (seharusnya sama, asalkan posisi tetap)

Bedanya Alice-Bob dengan Eve:
- Alice & Bob = end-to-end RSSI (yang mereka ukur saat exchange)
- Eve = eavesdropper RSSI (ukur dari tempat Eve)
