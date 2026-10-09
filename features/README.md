# Features

Folder ini berisi **research & experiment** di atas library `rak3172` — bukan bagian dari library core, tapi contoh real-world use case yang lebih kompleks dari `examples/`.

## Subfolder

### `research/` — Alice, Bob, Eve (RSSI measurement)

**Apa:** Eksperimen RSSI measurement antara 3 RAK3172 module.

**Skenario:**
- Alice kirim ping ke Bob setiap interval
- Bob ukur RSSI ping, tunggu 100 ms, balas pong + RSSI-nya
- Alice ukur RSSI pong, catat data, ulangi
- Eve dengarkan semua frame, catat RSSI dari perspektif eavesdropper

**Struktur:**
```
research/
  ├─ payloads/
  │  ├─ probe.py         Probe: "<seq>;<rssi>" (ping/pong payload)
  │  └─ README.md        Penjelasan Probe class
  │
  ├─ handlers/
  │  ├─ alice_handler.py AliceHandler (node side, terima pong)
  │  ├─ bob_handler.py   BobHandler (gateway side, terima ping & balas)
  │  ├─ eve_handler.py   EveHandler (listener side, hanya catat)
  │  └─ README.md        Penjelasan tiap handler, method, tweak, thread safety
  │
  └─ __init__.py
```

**Entry points di root `features/`:**
- `alice.py` — Run Alice (node): `python features/alice.py`
- `bob.py` — Run Bob (gateway): `python features/bob.py`
- `eve.py` — Run Eve (listener): `python features/eve.py`

**Output:**
```
# Terminal Bob:
[bob] ping #1 from 2: rssi=-70 snr=7
[bob] ping #2 from 2: rssi=-68 snr=6
...

# Terminal Alice:
[alice] pong #1: rssi_at_bob=-70 rssi_at_alice=-65 snr=7
[alice] pong #2: rssi_at_bob=-68 rssi_at_alice=-63 snr=6
...

# Terminal Eve:
[eve] alice -> bob ping #1: rssi=-70 snr=7
[eve] bob -> alice pong #1: rssi=-65 snr=7
[eve] alice -> bob ping #2: rssi=-68 snr=6
...
```

**Dokumentasi:**
- [research/README.md](research/README.md) — Setup, alur, tweaking
- [research/payloads/README.md](research/payloads/README.md) — Probe class detail
- [research/handlers/README.md](research/handlers/README.md) — Handler detail, thread safety, method docs

**Status:** Belum ditest di hardware RAK3172 asli.

---

## Filosofi

Folder `features/` adalah tempat **experiment yang belum production-ready**:
- Bukan bagian dari library core (`rak3172/`)
- Lebih kompleks dari quick example (`examples/`)
- Contoh best practice: payloads, handlers, entry point (wiring), threading, sync
- Dokumentasi lengkap supaya bisa di-fork/customize untuk project lain

Berbeda dengan `examples/`:
- `examples/` = minimal, cepat dijalankan, focus satu hal saja
- `features/` = full pattern, multi-component, show best practice

---

## Menambah experiment baru

Jika mau research lain di folder ini, ikuti pola yang sama:

```
features/
  ├─ experiment_name/
  │  ├─ payloads/
  │  │  ├─ *.py
  │  │  └─ README.md
  │  │
  │  ├─ handlers/
  │  │  ├─ *.py
  │  │  └─ README.md
  │  │
  │  ├─ services/      (opsional, untuk business logic)
  │  │  └─ *.py
  │  │
  │  └─ __init__.py
  │
  ├─ entry_point_1.py
  ├─ entry_point_2.py
  ├─ entry_point_3.py
  └─ README.md        (setup, alur, tweak)
```

**Aturan:**
1. **Payloads** = kontrak pesan (bytes ↔ object)
2. **Handlers** = reaksi saat frame terima
3. **Services** (opsional) = business logic, decision-making (tidak I/O)
4. **Entry points** = wiring only (build device + handler, run forever)
5. **Dokumentasi** = README di setiap subfolder + root folder

Lihat `research/` sebagai template.
