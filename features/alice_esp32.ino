/**
 * Alice (ESP32 + RFM95): Send ping to Bob, wait for pong, measure RSSI, repeat.
 *
 * Wiring (ESP32):
 *   RFM95 NSS (CS) → GPIO 5  (ss)
 *   RFM95 RST     → GPIO 14 (rst)
 *   RFM95 DIO0    → GPIO 2  (dio0)
 *   RFM95 MOSI    → GPIO 23 (SPI default)
 *   RFM95 MISO    → GPIO 19 (SPI default)
 *   RFM95 SCK     → GPIO 18 (SPI default)
 *
 * Payload: "<seq>;<rssi>"
 *   - Ping (Alice → Bob): "1;" (rssi empty)
 *   - Pong (Bob → Alice): "1;-71" (rssi from Bob)
 *
 * Match radio config with Bob (RAK3172) and Eve (RAK3172):
 *   Frequency: 868 MHz
 *   Spreading Factor: 7
 *   Bandwidth: 125 kHz
 *   Coding Rate: 4/5
 *   Preamble: 8
 *
 * Expected output:
 *   [alice] pong #1: rssi_at_bob=-71 rssi_at_alice=-65
 *   [alice] pong #2: rssi_at_bob=-69 rssi_at_alice=-63
 *   ...
 */

#include <SPI.h>
#include <LoRa.h>

// ============ WIRING ============
#define SS 5     // NSS / CS
#define RST 14   // RESET
#define DIO0 2   // DIO0 (RX Done / TX Done)

// ============ LORA CONFIG ============
#define FREQUENCY 868E6      // 868 MHz (match with Bob & Eve)
#define SPREADING_FACTOR 7   // SF7 (match)
#define BANDWIDTH 125E3      // 125 kHz (match)
#define CODING_RATE 5        // CR 4/5 (match)
#define TX_POWER 17          // dBm (adjust as needed, max ~20)
#define PREAMBLE_LEN 8       // (match)

// ============ ADDRESSING ============
#define ALICE_ADDRESS 2      // This device
#define BOB_ADDRESS 1        // Gateway / target

// ============ TIMING ============
#define PONG_TIMEOUT_MS 5000 // Wait up to 5 seconds for pong
#define ROUND_DELAY_MS 100   // Delay between pong & next ping

// ============ STATE ============
volatile int rx_seq = -1;           // Expected seq for current pong
volatile float rssi_at_bob = 0.0;   // RSSI measured by Bob (from pong payload)
volatile float rssi_at_alice = 0.0; // RSSI measured by Alice (local measurement)
volatile bool pong_received = false;

unsigned long last_ping_time = 0;

// ============ SETUP ============
void setup() {
  Serial.begin(115200);
  delay(2000);  // Wait for Serial to stabilize

  Serial.println("\n[alice] ESP32 + RFM95 LoRa sender");
  Serial.printf("[alice] FREQ=%.0f Hz, SF=%d, BW=%.0f Hz, CR=4/%d\n",
                FREQUENCY, SPREADING_FACTOR, BANDWIDTH, CODING_RATE);

  // Initialize LoRa
  LoRa.setPins(SS, RST, DIO0);

  if (!LoRa.begin(FREQUENCY)) {
    Serial.println("[alice] FAILED to initialize LoRa!");
    while (1) delay(1000);
  }

  // Configure radio to match Bob & Eve
  LoRa.setSpreadingFactor(SPREADING_FACTOR);
  LoRa.setSignalBandwidth(BANDWIDTH);
  LoRa.setCodingRate4(CODING_RATE);
  LoRa.setPreambleLength(PREAMBLE_LEN);
  LoRa.setTxPower(TX_POWER);

  // Important: Sync word must match Bob & Eve
  // Default is 0x34 (LoRaWAN), change to 0x12 if Bob uses it
  LoRa.setSyncWord(0x12);

  Serial.println("[alice] LoRa initialized OK");
}

// ============ MAIN LOOP ============
void loop() {
  static int seq = 0;

  // Check for incoming packets (pong from Bob)
  int packet_size = LoRa.parsePacket();
  if (packet_size) {
    handle_receive(packet_size);
  }

  // Time to send next ping?
  unsigned long now = millis();
  if (now - last_ping_time >= ROUND_DELAY_MS) {
    seq++;
    send_ping(seq);
    last_ping_time = now;

    // Wait for pong
    if (wait_for_pong(PONG_TIMEOUT_MS)) {
      Serial.printf("[alice] pong #%d: rssi_at_bob=%.0f rssi_at_alice=%.0f\n",
                    seq, rssi_at_bob, rssi_at_alice);
    } else {
      Serial.printf("[alice] pong #%d TIMEOUT (no reply from Bob)\n", seq);
    }
  }

  delay(10);  // Small delay to avoid blocking
}

// ============ SEND PING ============
void send_ping(int seq) {
  // Payload: "<seq>;"  (rssi empty for ping)
  String payload = String(seq) + ";";

  LoRa.beginPacket();
  LoRa.write(ALICE_ADDRESS);  // from_addr
  LoRa.write(BOB_ADDRESS);    // to_addr
  LoRa.print(payload);        // payload
  LoRa.endPacket();

  Serial.printf("[alice] sent ping #%d\n", seq);
}

// ============ HANDLE RECEIVE ============
void handle_receive(int packet_size) {
  // Frame format: [from:1][to:1][payload:N]
  if (packet_size < 3) return;  // Too short

  byte from_addr = LoRa.read();
  byte to_addr = LoRa.read();

  // Only process if addressed to us (Alice)
  if (to_addr != ALICE_ADDRESS) return;

  // Read payload
  String payload = "";
  while (LoRa.available()) {
    payload += (char)LoRa.read();
  }

  // Parse payload: "<seq>;<rssi>"
  int semicolon_pos = payload.indexOf(';');
  if (semicolon_pos < 0) return;  // Malformed

  int seq = payload.substring(0, semicolon_pos).toInt();
  String rssi_str = payload.substring(semicolon_pos + 1);

  // Check if this is the pong we're waiting for
  if (seq != rx_seq) return;  // Not our sequence

  // rssi_str is the RSSI that Bob measured (can be empty for echo, but we expect it here)
  if (rssi_str.length() > 0) {
    rssi_at_bob = rssi_str.toFloat();
  }

  // Measure local RSSI (what Alice hears)
  rssi_at_alice = (float)LoRa.packetRssi();

  // Signal that pong arrived
  pong_received = true;
}

// ============ WAIT FOR PONG ============
bool wait_for_pong(unsigned long timeout_ms) {
  pong_received = false;
  rx_seq = -1;  // Will be set by send_ping before calling this

  // Extract seq from last sent ping
  // (In real code, track seq separately; here we use a counter)
  static int last_seq = 0;
  last_seq++;
  rx_seq = last_seq;

  unsigned long start = millis();
  while (millis() - start < timeout_ms) {
    int packet_size = LoRa.parsePacket();
    if (packet_size) {
      handle_receive(packet_size);
      if (pong_received) return true;
    }
    delay(10);
  }

  return false;  // Timeout
}
