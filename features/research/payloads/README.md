# Payloads: Probe

## Apa itu Probe?

`Probe` adalah **kontrak pesan** (wire format) untuk komunikasi ping-pong antara Alice dan Bob. Satu kelas yang dipahami kedua belah pihak supaya tidak bisa salah tulis format.

## Struktur data

```python
@dataclass
class Probe(Payload):
    seq: int                        # Nomor urut frame (1, 2, 3, ...)
    rssi: Optional[float] = None    # RSSI yang diukur di sisi penerima (kosong untuk ping, terisi untuk pong)
```

## Format wire (bytes)

```
"<seq>;<rssi>"
```

### Contoh

| Apa | seq | rssi | Bytes | Keterangan |
|---|---|---|---|---|
| Alice kirim ping ke Bob | 5 | None | `b"5;"` | RSSI kosong (belum ada balasan) |
| Bob balas pong ke Alice | 5 | -71.0 | `b"5;-71"` | RSSI yang Bob ukur saat terima ping Alice |

## Metode

### `to_payload() -> bytes`

**Kegunaan:** Encode object `Probe` menjadi bytes untuk dikirim via LoRa.

```python
probe = Probe(seq=5, rssi=None)
payload = probe.to_payload()  # b"5;"

probe_pong = Probe(seq=5, rssi=-71.0)
payload = probe_pong.to_payload()  # b"5;-71"
```

**Wajib:** Ya, dipanggil di Alice dan Bob sebelum `send()`.

**Tweak:** Format `rssi` dibulatkan ke integer (`{rssi:.0f}`). Kalau perlu presisi lebih tinggi, ubah ke `{rssi:.1f}` dll.

---

### `from_payload(payload: bytes) -> Optional[Probe]`

**Kegunaan:** Decode bytes yang diterima menjadi object `Probe`. Return `None` jika format salah, jangan raise exception (supaya satu frame rusak tidak mati handler).

```python
payload = b"5;"
probe = Probe.from_payload(payload)  # Probe(seq=5, rssi=None)

payload = b"5;-71"
probe = Probe.from_payload(payload)  # Probe(seq=5, rssi=-71.0)

payload = b"invalid"
probe = Probe.from_payload(payload)  # None (malformed, ditangkap di handler)
```

**Wajib:** Ya, handler payloadnya memanggil ini otomatis (di `PayloadHandler.handle()`).

**Tweak:** Ubah delimiter `;` atau format urutan field jika perlu.

---

## Kapan pakai apa

| Situasi | Gunakan |
|---|---|
| Sebelum kirim frame | `probe = Probe(...)`  → `probe.to_payload()` → `send()` |
| Setelah terima frame | `handler` → `PayloadHandler.on_payload()` dapat object `Probe` siap pakai |

## Hubungan dengan handler

```
Alice (node)                                 Bob (gateway)
    ↓                                             ↓
AliceHandler.expect(seq)   ———————— ping ————→  BobHandler.on_payload()
                                 Probe(5)       ├─ ukur rssi
                           ←———— pong ———────┤  └─ balas Probe(5, rssi=-71)
AliceHandler.wait_pong()        Probe(5,-71)
```

- Alice punya handler buat terima balasan Bob (pong) dan ukur RSSI-nya.
- Bob punya handler buat terima ping Alice, ukur RSSI, lalu balas dengan RSSI itu embed di pong.
- Payload `Probe` adalah apa yang diterbangkan.

## Penting

- **Satu kelas untuk ping dan pong.** Dibedakan dari alamat pengirim (`from_addr`) dan kehadiran `rssi`.
- **Field tidak boleh berubah.** Menambah/mengurangi field atau ubah urutan = protocol mismatch, semua device turun.
- **RSSI selalu Optional.** Ping dari Alice punya `rssi=None`, pong dari Bob punya `rssi=float`.
