# CSV Export untuk Alice dan Bob

Fitur CSV export memungkinkan Anda untuk menyimpan data koneksi LoRa (RSSI, SNR, timestamp) ke dalam file CSV untuk analisis lebih lanjut.

## Penggunaan

### Alice (Node)

Jalankan Alice dengan output CSV default:
```bash
LORA_ADDRESS=2 LORA_GATEWAY_ADDRESS=1 python features/alice.py
```

Data akan disimpan ke `alice_connection_data.csv` (default).

Untuk menyimpan ke file custom:
```bash
LORA_ADDRESS=2 LORA_GATEWAY_ADDRESS=1 CSV_FILE=/path/to/custom_alice_data.csv python features/alice.py
```

**Format CSV Alice:**
```
timestamp,seq,rssi_at_bob,rssi_at_alice,snr
2026-10-09T14:30:45.123456,1,-75.0,-85.0,8.5
2026-10-09T14:30:45.234567,2,-74.0,-84.0,8.7
```

| Kolom | Deskripsi |
|-------|-----------|
| `timestamp` | ISO 8601 timestamp saat pong diterima |
| `seq` | Nomor urut ping/pong |
| `rssi_at_bob` | RSSI yang diukur Bob ketika menerima ping dari Alice |
| `rssi_at_alice` | RSSI yang diukur Alice ketika menerima pong dari Bob |
| `snr` | Signal-to-Noise Ratio pada pong yang diterima Alice |

### Bob (Gateway)

Jalankan Bob dengan output CSV default:
```bash
LORA_ADDRESS=1 python features/bob.py
```

Data akan disimpan ke `bob_connection_data.csv` (default).

Untuk menyimpan ke file custom:
```bash
LORA_ADDRESS=1 CSV_FILE=/path/to/custom_bob_data.csv python features/bob.py
```

**Format CSV Bob:**
```
timestamp,seq,from_addr,rssi,snr
2026-10-09T14:30:45.123456,1,2,-85.0,8.5
2026-10-09T14:30:45.234567,2,2,-84.0,8.7
```

| Kolom | Deskripsi |
|-------|-----------|
| `timestamp` | ISO 8601 timestamp saat ping diterima |
| `seq` | Nomor urut ping |
| `from_addr` | Alamat node pengirim (Alice) |
| `rssi` | RSSI yang diukur Bob ketika menerima ping dari Alice |
| `snr` | Signal-to-Noise Ratio pada ping yang diterima Bob |

## Contoh Penggunaan untuk Testing

### Setup dasar (dua terminal)

**Terminal 1 - Bob (Gateway):**
```bash
cd /Users/ktyudha/Projects/ta/multihoplora/rak3172-lib
LORA_ADDRESS=1 python features/bob.py
```

**Terminal 2 - Alice (Node):**
```bash
cd /Users/ktyudha/Projects/ta/multihoplora/rak3172-lib
LORA_ADDRESS=2 LORA_GATEWAY_ADDRESS=1 python features/alice.py
```

Data akan dikumpulkan ke:
- `bob_connection_data.csv` - data pings yang diterima Bob
- `alice_connection_data.csv` - data pongs yang diterima Alice

### Custom output location

```bash
# Terminal 1 - Bob
LORA_ADDRESS=1 CSV_FILE=./logs/bob_2026-10-09.csv python features/bob.py

# Terminal 2 - Alice
LORA_ADDRESS=2 LORA_GATEWAY_ADDRESS=1 CSV_FILE=./logs/alice_2026-10-09.csv python features/alice.py
```

## Analisis Data

Setelah mengumpulkan data, Anda dapat menganalisisnya dengan Python atau tool lainnya:

```python
import pandas as pd

# Baca data Alice
alice_df = pd.read_csv('alice_connection_data.csv')

# Analisis RSSI
print(f"Average RSSI at Bob: {alice_df['rssi_at_bob'].mean():.1f} dBm")
print(f"Average RSSI at Alice: {alice_df['rssi_at_alice'].mean():.1f} dBm")
print(f"Average SNR: {alice_df['snr'].mean():.2f} dB")
print(f"Path loss: {(alice_df['rssi_at_bob'] - alice_df['rssi_at_alice']).mean():.1f} dB")
```

## Thread Safety

CSV writing adalah thread-safe. Setiap handler menggunakan lock untuk memastikan data tidak tercorrupt ketika ditulis dari multiple threads.

## Performance

CSV writing dilakukan secara asynchronous dan tidak memblok packet reception atau transmission.
