# Research: Alice, Bob, Eve

RSSI measurement experiment antara tiga RAK3172 module (P2P, same radio settings).

## Quick start

```bash
# Terminal 1: Start Bob (gateway)
LORA_ADDRESS=1 python features/bob.py

# Terminal 2: Start Eve (listener)
LORA_ADDRESS=3 python features/eve.py

# Terminal 3: Start Alice (node)
LORA_ADDRESS=2 LORA_GATEWAY_ADDRESS=1 python features/alice.py
```

**Output example:**
```
[bob] ping #1 from 2: rssi=-70 snr=7
[eve] alice -> bob ping #1: rssi=-70 snr=7
[eve] bob -> alice pong #1: rssi=-65 snr=7
[alice] pong #1: rssi_at_bob=-70 rssi_at_alice=-65 snr=7
```

---

## Dokumentasi

- **[README_DETAILED.md](README_DETAILED.md)** — Setup lengkap, alur, debug, tweaking
- **[payloads/README.md](payloads/README.md)** — `Probe` class: structure, metode, format wire
- **[handlers/README.md](handlers/README.md)** — `AliceHandler`, `BobHandler`, `EveHandler`: tanggung jawab, metode, thread safety, flow

---

## Struktur

```
research/
├─ payloads/
│  ├─ probe.py           Probe class: seq + rssi
│  └─ README.md
│
├─ handlers/
│  ├─ alice_handler.py   Terima pong, ukur RSSI
│  ├─ bob_handler.py     Terima ping, balas pong + RSSI
│  ├─ eve_handler.py     Dengarkan semua, log
│  └─ README.md
│
└─ __init__.py
```

---

## Component diagram

```
Alice --ping #N--> Bob          Bob measure RSSI
Alice <--pong #N-- Bob          reply after 100ms with RSSI
(repeat)                        Eve overhear both, measure RSSI
```

| Role | Device | Task |
|---|---|---|
| **Node** | Alice | Send ping, wait for pong, measure RSSI at Alice |
| **Gateway** | Bob | Receive ping, measure RSSI, reply pong with RSSI at Bob |
| **Listener** | Eve | Receive all frames, measure RSSI, log only (no reply) |

---

## Key files

| File | Apa | Jalankan dengan |
|---|---|---|
| [../alice.py](../alice.py) | Entry Alice (loop send + wait) | `LORA_ADDRESS=2 LORA_GATEWAY_ADDRESS=1 python features/alice.py` |
| [../bob.py](../bob.py) | Entry Bob (gateway, wait for ping) | `LORA_ADDRESS=1 python features/bob.py` |
| [../eve.py](../eve.py) | Entry Eve (listener only) | `LORA_ADDRESS=3 python features/eve.py` |

---

## Penting

- **Belum ditest** di hardware RAK3172 asli (cek encode/decode, import, compile only).
- **Delay 100 ms adalah target.** RX re-arm ambil ~1 s, jadi round time sesungguhnya lebih lama.
- **Eve pakai bare `LoRaP2P`**, bukan role gateway/node (supaya tidak filter frame).
- **Thread safety:** Bob pakai thread terpisah untuk `reply()`, Alice pakai `Event` untuk sync.

---

Lihat [README_DETAILED.md](README_DETAILED.md) untuk setup lengkap, troubleshooting, tweak, dan analisis data.

---

## Alternative: ESP32 Alice

Jika Alice gunakan **ESP32 + RFM95** (bukan RAK3172):
- Payload format tetap sama (`<seq>;<rssi>`)
- Frame header tetap sama (`[from][to][payload]`)
- Bob & Eve tidak perlu berubah
- Lihat [CROSS_PLATFORM.md](CROSS_PLATFORM.md) untuk wiring, config, debugging
