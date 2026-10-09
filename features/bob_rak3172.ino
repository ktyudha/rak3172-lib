/**
 * Bob (RAK3172 RUI3): Receive ping from Alice, measure RSSI, send pong with RSSI.
 *
 * Role: Gateway. Responds to Alice's pings.
 *
 * Address:
 *   Bob = 1 (receiver)
 *   Alice = 2 (sender)
 *
 * Payload format: "<seq>;<rssi>"
 *   - Ping (Alice → Bob): "1;" (rssi empty)
 *   - Pong (Bob → Alice): "1;-71" (rssi from Bob)
 *
 * Expected output:
 *   [bob] ping #1 from 2: rssi=-71 snr=7
 *   [bob] ping #2 from 2: rssi=-69 snr=6
 *   ...
 *
 * Based on RUI3 LoRa P2P example
 */

// ============ ADDRESS ============
#define BOB_ADDRESS 1
#define ALICE_ADDRESS 2
#define EVE_ADDRESS 3

// ============ LORA CONFIG ============
// Must match with Alice & Eve
double myFreq = 868000000;  // 868 MHz
uint16_t sf = 7;            // Spreading Factor 7
uint16_t bw = 125E3;        // Bandwidth 125 kHz
uint16_t cr = 5;            // Coding Rate 4/5
uint16_t preamble = 8;      // Preamble length
uint16_t txPower = 2;       // TX power

// ============ TIMING ============
#define REPLY_DELAY_MS 100  // Delay before sending pong (milliseconds)

// ============ RECEIVE CALLBACK ============
/**
 * Called when a P2P frame is received.
 * Bob measures RSSI, then queues pong reply.
 */
void recv_cb(rui_lora_p2p_recv_t data)
{
  if (data.BufferSize < 3) {
    return;  // Frame too short
  }

  // Parse frame: [from_addr:1][to_addr:1][payload:N]
  uint8_t from_addr = data.Buffer[0];
  uint8_t to_addr = data.Buffer[1];

  // Only process if addressed to us (Bob)
  if (to_addr != BOB_ADDRESS) {
    return;
  }

  // Only process if from Alice (expected sender)
  if (from_addr != ALICE_ADDRESS) {
    return;
  }

  // Measure RSSI when received (this is when Bob receives Alice's ping)
  int16_t rssi_measured = data.Rssi;
  int8_t snr_measured = data.Snr;

  // Extract payload from ping
  int payload_len = data.BufferSize - 2;
  char payload[payload_len + 1];
  memcpy(payload, data.Buffer + 2, payload_len);
  payload[payload_len] = '\0';

  // Parse payload: "<seq>;"  (rssi should be empty for ping)
  String payload_str = String(payload);
  payload_str.trim();
  int semicolon_pos = payload_str.indexOf(';');
  if (semicolon_pos < 0) {
    return;  // Malformed
  }

  int seq = payload_str.substring(0, semicolon_pos).toInt();

  // Log the ping
  Serial.printf("[bob] ping #%d from %d: rssi=%d snr=%d\n",
                seq, from_addr, rssi_measured, snr_measured);

  // Wait before sending pong (to allow Alice to return to RX mode)
  delay(REPLY_DELAY_MS);

  // Send pong with RSSI that Bob measured
  send_pong(seq, rssi_measured);

  // Go back to RX mode
  delay(100);
  api.lora.precv(0);
}

// ============ SEND CALLBACK ============
void send_cb(void)
{
  // Re-arm RX after send
  api.lora.precv(65534);
}

// ============ SEND PONG ============
void send_pong(int seq, int rssi_value)
{
  // Build packet: [from_addr][to_addr][payload]
  // Payload: "<seq>;<rssi>"  (rssi is RSSI that Bob measured)

  String payload_str = String(seq) + ";" + String(rssi_value);
  uint8_t packet[128];

  packet[0] = BOB_ADDRESS;    // from_addr
  packet[1] = ALICE_ADDRESS;  // to_addr

  // Copy payload to packet
  int payload_len = payload_str.length();
  for (int i = 0; i < payload_len; i++) {
    packet[2 + i] = payload_str[i];
  }

  int total_len = 2 + payload_len;

  // Send packet
  bool sent = api.lora.psend(total_len, packet);
  // (Silent on success, simplicity)
  if (!sent) {
    Serial.printf("[bob] pong #%d FAILED to send\n", seq);
  }
}

// ============ SETUP ============
void setup()
{
  Serial.begin(115200);
  delay(2000);

  Serial.println("\n[bob] RAK3172 LoRa P2P Gateway");
  Serial.println("Role: Gateway (receiver + responder)");
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

  Serial.printf("  Reply delay: %d ms\n", REPLY_DELAY_MS);

  // Register callbacks
  api.lora.registerPRecvCallback(recv_cb);
  api.lora.registerPSendCallback(send_cb);

  // Start listening
  Serial.println("\nStarting RX mode (listening for pings)...");
  bool rx_ok = api.lora.precv(65534);  // 65534 = continuous RX
  Serial.printf("RX mode: %s\n", rx_ok ? "OK (listening)" : "FAIL");

  Serial.println("\n[bob] Waiting for pings from alice...\n");
}

// ============ LOOP ============
void loop()
{
  // Bob just waits for pings. All work is done in recv_cb().
  delay(1000);
}
