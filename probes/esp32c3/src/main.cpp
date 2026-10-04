#include <Arduino.h>
#include <WiFi.h>
#include <esp_heap_caps.h>
#include <esp_netif_net_stack.h>
#include <lwip/netif.h>
#include <lwip/tcpip.h>
#include <WiFiUdp.h>
#include <atomic>
#ifdef LAB_TCP_DF
#include "pr/TcpDontFragment.h"
#endif

static netif_output_fn realOutput = nullptr;
static std::atomic<unsigned> tcpPackets{0};
static std::atomic<unsigned> tcpDfPackets{0};
static std::atomic<unsigned> udpPackets{0};
static std::atomic<unsigned> udpDfPackets{0};
static std::atomic<unsigned> invalidChecksums{0};

// Observe the final IPv4 header passed by the PR to the original netif output.
static err_t captureOutput(struct netif* iface, struct pbuf* p, const ip4_addr_t* ip) {
  if (p->len >= 20) {
    const auto* bytes = static_cast<const uint8_t*>(p->payload);
    const unsigned length = (bytes[0] & 15) * 4;
    if ((bytes[0] >> 4) == 4 && length >= 20 && length <= p->len) {
      const bool df = (bytes[6] & 0x40) != 0;
      if (bytes[9] == 6) { ++tcpPackets; if (df) ++tcpDfPackets; }
      if (bytes[9] == 17) { ++udpPackets; if (df) ++udpDfPackets; }
      unsigned sum = 0;
      for (unsigned i = 0; i < length; i += 2) sum += (unsigned(bytes[i]) << 8) | bytes[i+1];
      while (sum >> 16) sum = (sum & 0xffff) + (sum >> 16);
      if (sum != 0xffff) ++invalidChecksums;
    }
  }
  return realOutput(iface, p, ip);
}

static void installCapture(void*) {
  auto* iface = static_cast<struct netif*>(esp_netif_get_netif_impl(WiFi.STA.netif()));
  if (iface && iface->output) { realOutput = iface->output; iface->output = captureOutput; }
}

// A controlled fragmentation workload: fixed metadata, fallible 2 KiB blocks.
// Deliberate heap use exercises the guest allocator; no reading behavior is modeled.
static void* blocks[128] = {};
static constexpr uint32_t CAPS = MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT;

static void sample(const char* phase, int cycle) {
  Serial.printf("LAB_HEAP {\"phase\":\"%s\",\"cycle\":%d,\"free\":%u,\"largest\":%u,\"minimum\":%u,\"integrity\":%s}\n",
                phase, cycle, heap_caps_get_free_size(CAPS), heap_caps_get_largest_free_block(CAPS),
                heap_caps_get_minimum_free_size(CAPS), heap_caps_check_integrity_all(true) ? "true" : "false");
  Serial.flush();
}

void setup() {
  Serial.begin(115200);
  delay(100);
  Serial.printf("LAB_START {\"idf\":\"%s\",\"chip\":\"ESP32-C3\",\"wifi_driver_substituted\":false}\n", esp_get_idf_version());
  sample("baseline", -1);
  int allocated = 0;
  for (auto& block : blocks) {
    block = heap_caps_malloc(2048, CAPS);
    if (!block) break;
    ++allocated;
  }
  Serial.printf("LAB_ALLOCATED %d\n", allocated);
  sample("allocated", -1);
  for (int i = 0; i < 128; i += 2) {
    heap_caps_free(blocks[i]);
    blocks[i] = nullptr;
  }
  sample("holes", -1);
  const size_t request = heap_caps_get_largest_free_block(CAPS) + 1024;
  void* large = heap_caps_malloc(request, CAPS);
  Serial.printf("LAB_LARGE {\"requested\":%u,\"free_before\":%u,\"success\":%s}\n", unsigned(request),
                unsigned(heap_caps_get_free_size(CAPS)), large ? "true" : "false");
  heap_caps_free(large);
  for (auto& block : blocks) {
    heap_caps_free(block);
    block = nullptr;
  }
  sample("released", -1);
  for (int cycle = 0; cycle < 3; ++cycle) {
    sample("before_wifi", cycle);
    WiFi.mode(WIFI_STA);
    WiFi.begin("myssid", "mypassword");
    const unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) delay(20);
    Serial.printf("LAB_WIFI {\"cycle\":%d,\"connected\":%s,\"status\":%d,\"ip\":\"%s\"}\n", cycle,
                  WiFi.status() == WL_CONNECTED ? "true" : "false", int(WiFi.status()), WiFi.localIP().toString().c_str());
    sample("wifi_active", cycle);
    if (WiFi.status() == WL_CONNECTED) {
      tcpPackets = tcpDfPackets = udpPackets = udpDfPackets = invalidChecksums = 0;
      tcpip_callback(installCapture, nullptr);
      delay(50);
#ifdef LAB_TCP_DF
      applyTcpDontFragment();
      applyTcpDontFragment();  // exercise idempotent installation
      delay(50);
#endif
      WiFiUDP udp;
      udp.beginPacket(IPAddress(192, 168, 4, 1), 8089);
      udp.write(reinterpret_cast<const uint8_t*>("LAB UDP"), 7);
      udp.endPacket();
      udp.stop();
      WiFiClient client;
      const bool connected = client.connect(IPAddress(192, 168, 4, 1), 8088, 3000);
      bool response = false;
      if (connected) {
        client.print("GET /probe HTTP/1.1\r\nHost: lab\r\nConnection: close\r\n\r\n");
        const unsigned long deadline = millis();
        while (!client.available() && millis() - deadline < 3000) delay(10);
        const String line = client.readStringUntil('\n');
        response = line.startsWith("HTTP/1.0 200");
        client.stop();
      }
      Serial.printf("LAB_TCP {\"cycle\":%d,\"connected\":%s,\"http_200\":%s}\n", cycle,
                    connected ? "true" : "false", response ? "true" : "false");
    }
    Serial.printf("LAB_PACKETS {\"cycle\":%d,\"tcp\":%u,\"tcp_df\":%u,\"udp\":%u,\"udp_df\":%u,\"bad_ip_checksums\":%u}\n",
                  cycle, tcpPackets.load(), tcpDfPackets.load(), udpPackets.load(), udpDfPackets.load(), invalidChecksums.load());
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    delay(200);
    sample("wifi_off", cycle);
  }
  Serial.println("LAB_DONE");
  Serial.flush();
}

void loop() { delay(1000); }
