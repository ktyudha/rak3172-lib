# Handlers: Reaksi terhadap frame yang diterima

Handler adalah **kelas yang bereaksi** saat device menerima frame LoRa. Setiap handler punya tujuan berbeda sesuai perannya di skenario Alice-Bob-Eve.

---

## AliceHandler

**Peran:** Node yang kirim ping ke Bob, terima pong dari Bob, ukur RSSI pong itu.

### Tanggung jawab

1. **Terima pong dari Bob** → `on_payload(from_addr, message, rssi, snr)`
2. **Ukur RSSI pong** → simpan di `rssi_at_alice`
3. **Simpan RSSI yang Bob ukur** dari field `message.rssi` → simpan di `rssi_at_bob`
4. **Bangunkan loop sender** yang sedang menunggu dengan `threading.Event`

### Metode

#### `__init__()`
```python
handler = AliceHandler()
```
**Kegunaan:** Inisialisasi handler. Tidak perlu parameter.

**Field penting:**
- `_pong: threading.Event` — Event untuk sync antara thread penerima dan sender
- `_seq: int` — Nomor urut yang sedang ditunggu (untuk ignore pong dari round lalu)
- `rssi_at_bob: Optional[float]` — RSSI yang Bob ukur saat terima ping Alice
- `rssi_at_alice: Optional[float]` — RSSI yang Alice ukur saat terima pong Bob

**Wajib:** Ya, selalu buat handler sebelum pass ke `P2PNode`.

---

#### `expect(seq: int)`
```python
handler.expect(5)  # menunggu pong #5
```

**Kegunaan:** Beritahu handler bahwa ping #N baru saja dikirim. Handler akan ignore pong dari round sebelumnya.

**Harus dipanggil:** Sebelum `node.send_to_gateway(ping_bytes)`, supaya pong yang diterima cocok dengan seq yang kita kirim.

```python
seq = 1
handler.expect(seq)
node.send_to_gateway(Probe(seq).to_payload())
```

**Tweak:** Kalau ingin strict (ignore pong yang tidak cocok), sudah built-in di `on_payload()` dengan `if message.seq != self._seq: return`.

---

#### `wait_pong(timeout: float) -> bool`
```python
ok = handler.wait_pong(timeout=5.0)
if ok:
    print(f"rssi_at_bob={handler.rssi_at_bob}, rssi_at_alice={handler.rssi_at_alice}")
else:
    print("timeout, Bob tidak menjawab")
```

**Kegunaan:** Block sampai pong #N diterima, atau timeout jika terlalu lama.

**Return:** `True` jika pong datang sebelum timeout, `False` jika timeout.

**Wajib:** Ya, di loop sender Alice untuk tahu kapan boleh kirim ping berikutnya.

**Tweak:** 
- Timeout default di script adalah 5 detik. Ubah di parameter `wait_pong()` kalau module lebih lambat.
- Jika perlu retry, bisa extend timeout atau cek `handler.rssi_at_bob is None` setelah timeout.

---

#### `on_payload(from_addr, message, rssi, snr)`
```python
# Dipanggil otomatis oleh library saat frame diterima
# from_addr = 1 (Bob)
# message = Probe(seq=5, rssi=-71.0)
# rssi = "-60" (yang Alice ukur)
# snr = "7"
```

**Kegunaan:** Decode pong, ukur RSSI lokal, bangunkan sender yang sedang di `wait_pong()`.

**Dijalankan di:** RX thread (jangan kirim AT command dari sini, gunakan thread baru).

**Wajib:** Ya, ini method abstract yang harus di-override dari `PayloadHandler`.

**Jangan tweak:** Logika sudah benar. Kalau perlu custom behavior (misalnya log lebih detail), override atau extend.

---

## BobHandler

**Peran:** Gateway yang terima ping dari Alice, ukur RSSI ping itu, balas pong dengan RSSI yang dia ukur.

### Tanggung jawab

1. **Terima ping dari Alice** → `on_payload(from_addr, message, rssi, snr)`
2. **Ukur RSSI ping** → baca dari parameter `rssi`
3. **Tunggu delay** (default 100 ms) → biar protocol lebih clear
4. **Balas pong ke Alice** yang membawa RSSI Bob

### Metode

#### `__init__(reply_delay: float = 0.1)`
```python
handler = BobHandler(reply_delay=0.1)  # 100 ms
```

**Kegunaan:** Inisialisasi handler dengan setting delay sebelum balasan.

**Parameter:**
- `reply_delay` — Waktu tunggu (detik) sebelum Bob kirim pong ke Alice. Default 0.1 s (100 ms).

**Wajib:** Ya, selalu buat handler sebelum pass ke `P2PGateway`.

**Tweak:** Ubah `reply_delay` kalau perlu timing berbeda:
- 0.05 → 50 ms (lebih cepat)
- 0.2 → 200 ms (lebih lambat)
- 0.0 → tidak ada delay (tapi tidak realistis, kejar timing hardware)

**Catatan:** Delay adalah *target* saja. Re-arm RX setelah receive bisa memakan ~1 s, jadi round time asli bisa jauh lebih lama dari yang ada di setting.

---

#### `on_payload(from_addr, message, rssi, snr)`
```python
# Dipanggil otomatis saat Alice kirim ping
# from_addr = 2 (Alice)
# message = Probe(seq=5, rssi=None)
# rssi = "-70" (yang Bob ukur)
```

**Kegunaan:** Ukur RSSI ping, spawn thread buat delay + balas pong.

**Dijalankan di:** RX thread (aman, karena `_pong()` dipindah ke thread baru).

**Wajib:** Ya, method abstract dari `PayloadHandler`.

---

#### `_pong(to_addr, seq, rssi)` [private]
```python
# Dipanggil dari thread terpisah, bukan RX thread
```

**Kegunaan:** Tunggu delay, lalu kirim pong dengan RSSI yang diukur tadi.

**Dijalankan di:** Thread baru (daemon), safe untuk send AT command.

**Jangan tweak:** Ini implementation detail. Kalau mau ubah delay, ubah di `__init__` parameter saja.

---

## EveHandler

**Peran:** Listener murni (tidak punya address sendiri, tidak pernah kirim). Hanya dengarkan dan log semua frame Alice ↔ Bob.

### Tanggung jawab

1. **Terima SETIAP frame** (tanpa filter alamat tujuan)
2. **Parse Probe payload**
3. **Catat RSSI setiap frame**
4. **Print dengan label siapa kirim ke siapa**

### Metode

#### `__init__(names: Optional[Dict[int, str]] = None)`
```python
eve = EveHandler(names={1: "bob", 2: "alice"})
```

**Kegunaan:** Inisialisasi handler dengan mapping alamat → nama (opsional).

**Parameter:**
- `names` — Dict `{address: "display_name"}` untuk print yang lebih readable. Default `None` (print alamat numeric).

**Wajib:** Tidak, tapi sangat disarankan supaya log mudah dibaca.

**Contoh:**
```python
# Tanpa nama:
# [eve] 2 -> 1 ping #5: rssi=-60 snr=7

# Dengan nama:
# [eve] alice -> bob ping #5: rssi=-60 snr=7
```

---

#### `__call__(from_addr, to_addr, payload, rssi, snr)`
```python
# Dipanggil oleh LoRaP2P.on_receive
# from_addr = 2 (Alice)
# to_addr = 1 (Bob)
# payload = b"5;"
# rssi = "-60"
# snr = "7"
```

**Kegunaan:** Decode frame, print log dengan info lengkap.

**Dijalankan di:** RX thread, tapi tidak send AT command (aman).

**Wajib:** Ya, ini method yang dijalankan LoRaP2P saat dapat frame.

**Jangan tweak:** Kalau mau detail print berbeda, override atau extend method ini.

---

## Perbedaan dengan AliceHandler/BobHandler

| Aspek | Alice/Bob | Eve |
|---|---|---|
| **Interface** | `PayloadHandler` | Raw callback (tidak extends Handler) |
| **Pass ke** | `P2PNode(on_command=...)` / `P2PGateway(on_uplink=...)` | `LoRaP2P(on_receive=...)` |
| **Filter alamat** | Otomatis (hanya terima frame ke address diri sendiri) | Tidak ada filter (terima semuanya) |
| **Kirim frame** | Bisa pakai `reply()` | Tidak bisa (listener only) |
| **Parse payload** | Otomatis via `payload_type.from_payload()` | Manual dengan `Probe.from_payload()` |

---

## Hubungan antara handler

```
LoRaP2P (raw protocol layer)
  ├─ on_receive → EveHandler (listener, terima semua)
  └─ wrapped dalam P2PGateway/P2PNode
      ├─ P2PGateway → on_uplink → BobHandler
      └─ P2PNode → on_command → AliceHandler
```

**Event flow:**

```
Alice kirim ping
    ↓
LoRaP2P.on_receive (di RX thread)
    ├─ BobHandler.__call__() → on_payload() → _pong() di thread baru
    ├─ EveHandler.__call__() → log
    └─ AliceHandler.on_payload() (jika Alice juga dengar diri sendiri?)
        → set rssi_at_alice, bangunkan wait_pong()
```

---

## Konfigurasi/Tweak

### Tweak delay Bob
Edit `features/bob.py`:
```python
# Default 100 ms
P2PGateway.from_env(on_uplink=BobHandler(reply_delay=0.1)).run_forever()

# Ubah ke 50 ms
P2PGateway.from_env(on_uplink=BobHandler(reply_delay=0.05)).run_forever()
```

### Tweak timeout Alice
Edit `features/alice.py`:
```python
# Default 5 detik
PONG_TIMEOUT = 5.0

# Ubah ke 10 detik kalau module lambat
PONG_TIMEOUT = 10.0
```

### Tweak nama di Eve
Edit `features/eve.py`:
```python
# Sesuaikan dengan alamat di .env kalian
NAMES = {1: "bob", 2: "alice", 3: "eve"}
```

---

## Penting

1. **Handler hanya react, tidak inisiatif.** Alice yang aktif kirim ping; Bob hanya balas.
2. **RX thread jangan ada AT command.** Bob pakai thread terpisah untuk `reply()`, supaya tidak deadlock.
3. **Eve tidak punya `reply()`.** Dia tidak punya `device`, jadi tidak bisa kirim. Listener saja.
4. **Payload harus cocok.** AliceHandler dan BobHandler sama-sama pakai `payload_type = Probe`, jadi keduanya paham format yang sama.
