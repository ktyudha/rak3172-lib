/**
 * Eve (RAK3172 RUI3): Listen-only. Receive all frames, measure RSSI, log.
 *
 * Role: Eavesdropper. Measures RSSI/SNR of Alice↔Bob communication.
 *
 * Address:
 *   Alice = 2
 *   Bob = 1
 *   Eve = 3 (listener, can be any address not in use)
 *
 * Payload format: "<seq>;<rssi>"
 *   - Ping (Alice → Bob): "1;"
 *   - Pong (Bob → Alice): "1;-71"
 *
 * Expected output:
 *   [eve] alice -> bob ping #1: rssi=-70 snr=7
 *   [eve] bob -> alice pong #1: rssi=-65 snr=7
 *   ...
 *
 * Based on:
 *   https://github.com/Kongduino/RUI3_LoRa_P2P_PING_PONG
 */

// ============ ADDRESS ============
#define ALICE_ADDRESS 2
#define BOB_ADDRESS 1
#define EVE_ADDRESS 3

// ============ LORA CONFIG ============
// Must match with Alice (ESP32) & Bob (Python)
double myFreq = 868000000;  // 868 MHz
uint16_t sf = 7;            // Spreading Factor 7
uint16_t bw = 125E3;        // Bandwidth 125 kHz
uint16_t cr = 5;            // Coding Rate 4/5
uint16_t preamble = 8;      // Preamble length
uint16_t txPower = 2;       // TX power (not used, but set anyway)

// ============ STATE ============
const char* addr_name(uint8_t addr) {
  switch (addr) {
    case ALICE_ADDRESS: return "alice";
    case BOB_ADDRESS: return "bob";
    case EVE_ADDRESS: return "eve";
    default: return "?";
  }
}

// ============ RECEIVE CALLBACK ============
/**
 * Called when a P2P frame is received.
 * Eve logs all frames, regardless of address.
 */
void recv_cb(rui_lora_p2p_recv_t data)
{
  if (data.BufferSize == 0) {
    Serial.println("[eve] Empty buffer");
    return;
  }

  if (data.BufferSize < 3) {
    Serial.printf("[eve] Frame too short (%d bytes)\n", data.BufferSize);
    return;
  }

  // Parse frame: [from_addr:1][to_addr:1][payload:N]
  uint8_t from_addr = data.Buffer[0];
  uint8_t to_addr = data.Buffer[1];

  // Extract payload (rest of frame after 2-byte header)
  int payload_len = data.BufferSize - 2;
  char payload[payload_len + 1];
  memcpy(payload, data.Buffer + 2, payload_len);
  payload[payload_len] = '\0';

  // Trim whitespace
  String payload_str = String(payload);
  payload_str.trim();

  // Parse payload: "<seq>;<rssi>"
  int semicolon_pos = payload_str.indexOf(';');
  if (semicolon_pos < 0) {
    Serial.printf("[eve] Malformed payload from %s: %s\n",
                  addr_name(from_addr), payload_str.c_str());
    return;
  }

  int seq = payload_str.substring(0, semicolon_pos).toInt();
  String rssi_str = payload_str.substring(semicolon_pos + 1);

  // Determine frame type (ping vs pong)
  const char* frame_type = (rssi_str.length() == 0) ? "ping" : "pong";

  // Log frame
  Serial.printf("[eve] %s -> %s %s #%d: rssi=%d snr=%d\n",
                addr_name(from_addr),
                addr_name(to_addr),
                frame_type,
                seq,
                data.Rssi,
                data.Snr);

  // Go back to RX mode after processing
  delay(100);
  api.lora.precv(0);
}

// ============ SEND CALLBACK (not used, but required) ============
void send_cb(void)
{
  // Eve doesn't send, just re-arm RX
  api.lora.precv(65534);
}

// ============ SETUP ============
void setup()
{
  Serial.begin(115200);
  delay(2000);

  Serial.println("\n[eve] RAK3172 LoRa P2P Listener");
  Serial.println("Role: Eavesdropper (listen only, no transmission)");
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

  // Start listening (continuous RX mode)
  Serial.println("\nStarting RX mode (listening)...");
  bool rx_ok = api.lora.precv(65534);  // 65534 = continuous RX
  Serial.printf("RX mode: %s\n", rx_ok ? "OK (listening)" : "FAIL");

  Serial.println("\n[eve] Waiting for frames from alice and bob...\n");
}

// ============ LOOP ============
void loop()
{
  // Eve just waits for frames. All work is done in recv_cb().
  delay(1000);
}
