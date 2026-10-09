/**
 * Alice (RAK3172 RUI3): Send ping to Bob, wait for pong, measure RSSI, repeat.
 *
 * Role: Node. Initiates ping-pong cycle.
 *
 * Address:
 *   Alice = 2 (sender)
 *   Bob = 1 (receiver/gateway)
 *
 * Payload format: "<seq>;<rssi>"
 *   - Ping (Alice → Bob): "1;" (rssi empty)
 *   - Pong (Bob → Alice): "1;-71" (rssi from Bob)
 *
 * Expected output:
 *   [alice] sent ping #1
 *   [alice] pong #1: rssi_at_bob=-71 rssi_at_alice=-65
 *   [alice] sent ping #2
 *   ...
 *
 * Based on RUI3 LoRa P2P example
 */

// ============ ADDRESS ============
#define ALICE_ADDRESS 2
#define BOB_ADDRESS 1
#define EVE_ADDRESS 3

// ============ LORA CONFIG ============
// Must match with Bob & Eve
double myFreq = 868000000;  // 868 MHz
uint16_t sf = 7;            // Spreading Factor 7
uint16_t bw = 125E3;        // Bandwidth 125 kHz
uint16_t cr = 5;            // Coding Rate 4/5
uint16_t preamble = 8;      // Preamble length
uint16_t txPower = 2;       // TX power

// ============ TIMING ============
#define ROUND_DELAY_MS 100   // Delay between pong & next ping
#define PONG_TIMEOUT_MS 5000 // Wait max 5 seconds for pong

// ============ STATE ============
volatile int rx_seq = -1;           // Expected pong seq
volatile float rssi_at_bob = 0.0;   // RSSI from Bob (in pong payload)
volatile float rssi_at_alice = 0.0; // RSSI measured by Alice
volatile bool pong_received = false;

unsigned long last_ping_time = 0;
int current_seq = 0;

// ============ RECEIVE CALLBACK ============
/**
 * Called when a P2P frame is received.
 * Alice waits for pong from Bob.
 */
void recv_cb(rui_lora_p2p_recv_t data)
{
  if (data.BufferSize < 3) {
    return;  // Frame too short
  }

  // Parse frame: [from_addr:1][to_addr:1][payload:N]
  uint8_t from_addr = data.Buffer[0];
  uint8_t to_addr = data.Buffer[1];

  // Only process if addressed to us (Alice)
  if (to_addr != ALICE_ADDRESS) {
    return;
  }

  // Only process if from Bob (expected sender)
  if (from_addr != BOB_ADDRESS) {
    return;
  }

  // Extract payload
  int payload_len = data.BufferSize - 2;
  char payload[payload_len + 1];
  memcpy(payload, data.Buffer + 2, payload_len);
  payload[payload_len] = '\0';

  // Parse payload: "<seq>;<rssi>"
  String payload_str = String(payload);
  payload_str.trim();
  int semicolon_pos = payload_str.indexOf(';');
  if (semicolon_pos < 0) {
    return;  // Malformed
  }

  int seq = payload_str.substring(0, semicolon_pos).toInt();
  String rssi_str = payload_str.substring(semicolon_pos + 1);

  // Check if this is the pong we're waiting for
  if (seq != rx_seq) {
    return;  // Not our sequence
  }

  // Extract RSSI from Bob (he measured it when he received our ping)
  if (rssi_str.length() > 0) {
    rssi_at_bob = rssi_str.toFloat();
  }

  // Measure local RSSI (what Alice hears from pong)
  rssi_at_alice = (float)data.Rssi;

  // Signal that pong arrived
  pong_received = true;
}

// ============ SEND CALLBACK ============
void send_cb(void)
{
  // Re-arm RX after send
  api.lora.precv(65534);
}

// ============ SEND PING ============
void send_ping(int seq)
{
  // Build packet: [from_addr][to_addr][payload]
  // Payload: "<seq>;"  (rssi empty for ping)

  String payload_str = String(seq) + ";";
  uint8_t packet[128];

  packet[0] = ALICE_ADDRESS;  // from_addr
  packet[1] = BOB_ADDRESS;    // to_addr

  // Copy payload to packet
  int payload_len = payload_str.length();
  for (int i = 0; i < payload_len; i++) {
    packet[2 + i] = payload_str[i];
  }

  int total_len = 2 + payload_len;

  // Send packet
  bool sent = api.lora.psend(total_len, packet);
  if (sent) {
    Serial.printf("[alice] sent ping #%d\n", seq);
  } else {
    Serial.printf("[alice] ping #%d FAILED to send\n", seq);
  }
}

// ============ WAIT FOR PONG ============
bool wait_for_pong(unsigned long timeout_ms)
{
  pong_received = false;
  unsigned long start = millis();

  while (millis() - start < timeout_ms) {
    if (pong_received) {
      return true;
    }
    delay(10);
  }

  return false;  // Timeout
}

// ============ SETUP ============
void setup()
{
  Serial.begin(115200);
  delay(2000);

  Serial.println("\n[alice] RAK3172 LoRa P2P Sender");
  Serial.println("Role: Node (ping initiator)");
  Serial.println("======================================");

  // Check network mode (should be P2P mode = 0)
  if (api.lora.nwm.get() != 0) {
    Serial.printf("Switching to P2P mode...\n");
    api.lora.nwm.set(0);  // Set to P2P
    api.system.reboot();
  }

  // Print device info
  Serial.printf("Hardware ID: %s\n", api.system.chipId.get().c_str());
  Serial.printf("Model ID: %s\n", api.system.modelId.get().c_str());
  Serial.printf("Firmware Version: %s\n", api.system.firmwareVersion.get().c_str());

  // Configure radio
  Serial.println("\nConfiguring P2P radio:");

  Serial.printf("  Frequency: %.0f Hz (%.1f MHz) ... %s\n",
                myFreq, myFreq / 1e6,
                api.lora.pfreq.set(myFreq) ? "OK" : "FAIL");

  Serial.printf("  Spreading Factor: %d ... %s\n",
                sf,
                api.lora.psf.set(sf) ? "OK" : "FAIL");

  Serial.printf("  Bandwidth: %.0f Hz (%.0f kHz) ... %s\n",
                (double)bw, bw / 1e3,
                api.lora.pbw.set(bw) ? "OK" : "FAIL");

  Serial.printf("  Coding Rate: 4/%d ... %s\n",
                cr,
                api.lora.pcr.set(cr) ? "OK" : "FAIL");

  Serial.printf("  Preamble Length: %d ... %s\n",
                preamble,
                api.lora.ppl.set(preamble) ? "OK" : "FAIL");

  Serial.printf("  TX Power: %d dBm ... %s\n",
                txPower,
                api.lora.ptp.set(txPower) ? "OK" : "FAIL");

  // Register callbacks
  api.lora.registerPRecvCallback(recv_cb);
  api.lora.registerPSendCallback(send_cb);

  // Start listening (so we can receive pong from Bob)
  Serial.println("\nStarting RX mode (listening for pong)...");
  bool rx_ok = api.lora.precv(65534);
  Serial.printf("RX mode: %s\n", rx_ok ? "OK" : "FAIL");

  Serial.println("\n[alice] Ready. Starting ping loop...\n");
  last_ping_time = millis();
}

// ============ LOOP ============
void loop()
{
  unsigned long now = millis();

  // Time to send next ping?
  if (now - last_ping_time >= ROUND_DELAY_MS) {
    current_seq++;
    rx_seq = current_seq;  // Set expected pong seq

    send_ping(current_seq);
    last_ping_time = now;

    // Wait for pong
    if (wait_for_pong(PONG_TIMEOUT_MS)) {
      Serial.printf("[alice] pong #%d: rssi_at_bob=%.0f rssi_at_alice=%.0f\n",
                    current_seq, rssi_at_bob, rssi_at_alice);
    } else {
      Serial.printf("[alice] pong #%d TIMEOUT (no reply from bob)\n", current_seq);
    }
  }

  delay(10);
}
