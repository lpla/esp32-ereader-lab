#include <Arduino.h>
#include <WiFi.h>
#include <esp_heap_caps.h>
#include <esp_netif_net_stack.h>
#include <lwip/netif.h>
#include <lwip/tcpip.h>
#include <lwip/pbuf.h>
#include <lwip/inet_chksum.h>
#include <cstring>
#include <WiFiUdp.h>
#include <atomic>
#ifdef LAB_TCP_DF
#include "pr/TcpDontFragment.h"
#endif

static netif_output_fn realOutput = nullptr;
#ifdef LAB_PACKET_EDGES
static bool syntheticOutput = false;  // tcpip-task only
static uint8_t syntheticBytes[80] = {};
static uint16_t syntheticLength = 0;
static std::atomic<bool> edgesDone{false};
struct EdgeResult { const char* name; bool pass; };
static constexpr struct EdgeCase { const char* name; uint8_t vhl; uint8_t protocol; uint16_t flags; uint8_t length; bool unaligned; bool split; } edgeCases[] = {
  {"whole_tcp",0x45,6,0,20,false,false},
  {"unaligned_tcp",0x45,6,0,20,true,false},
  {"tcp_options",0x46,6,0,24,false,false},
  {"already_df",0x45,6,0x4000,20,false,false},
  {"more_fragments",0x45,6,0x2000,20,false,false},
  {"fragment_offset",0x45,6,1,20,false,false},
  {"udp",0x45,17,0,20,false,false},
  {"ipv6_tag",0x65,6,0,20,false,false},
  {"short_header",0x44,6,0,20,false,false},
  {"truncated",0x45,6,0,16,false,false},
  {"split_header",0x45,6,0,20,false,true},
};
static EdgeResult edgeResults[sizeof(edgeCases)/sizeof(edgeCases[0])] = {};
static uint8_t originalBytes[80] = {};
#endif
static std::atomic<unsigned> tcpPackets{0};
static std::atomic<unsigned> tcpDfPackets{0};
static std::atomic<unsigned> udpPackets{0};
static std::atomic<unsigned> udpDfPackets{0};
static std::atomic<unsigned> invalidChecksums{0};

// Observe the final IPv4 header passed by the PR to the original netif output.
static err_t captureOutput(struct netif* iface, struct pbuf* p, const ip4_addr_t* ip) {
#ifdef LAB_PACKET_EDGES
  if (syntheticOutput) {
    syntheticLength = pbuf_copy_partial(p, syntheticBytes, sizeof(syntheticBytes), 0);
    return ERR_OK;  // synthetic boundary packets do not enter the radio/ARP driver
  }
#endif
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

#ifdef LAB_PACKET_EDGES
// Run on the actual lwIP task through the installed PR callback. Fixed metadata
// avoids heap churn; tiny pbuf allocations exercise the real packet boundary.
static void runEdges(void*) {
  auto* iface = static_cast<struct netif*>(esp_netif_get_netif_impl(WiFi.STA.netif()));
  unsigned index = 0;
  for (const auto& c : edgeCases) {
    auto& result = edgeResults[index++];
    result.name = c.name; result.pass = false;
    pbuf* p = pbuf_alloc(PBUF_RAW, c.length + (c.unaligned ? 1 : 0), PBUF_RAM);
    if (!p) continue;
    if (c.unaligned) pbuf_remove_header(p, 1);
    memset(originalBytes, 0, sizeof(originalBytes));
    originalBytes[0]=c.vhl; originalBytes[2]=0; originalBytes[3]=c.length;
    originalBytes[4]=0x12; originalBytes[5]=0x34;
    originalBytes[6]=c.flags>>8; originalBytes[7]=c.flags;
    originalBytes[8]=64; originalBytes[9]=c.protocol;
    const unsigned header=(c.vhl&15)*4;
    if (header>=20 && header<=c.length) {
      const uint16_t sum=inet_chksum(originalBytes,header);
      memcpy(originalBytes+10,&sum,2);
    }
    memcpy(p->payload,originalBytes,c.length);
    pbuf* tail=nullptr;
    if (c.split) {
      tail=pbuf_alloc(PBUF_RAW,c.length-12,PBUF_RAM);
      if (!tail) {pbuf_free(p);continue;}
      memcpy(tail->payload,originalBytes+12,c.length-12);
      pbuf_realloc(p,12); pbuf_cat(p,tail);
    }
    syntheticLength=0; syntheticOutput=true;
    ip4_addr_t destination; IP4_ADDR(&destination,192,168,4,1);
    const err_t sent=iface->output(iface,p,&destination);
    syntheticOutput=false;
    const bool mutableHeader=c.protocol==6 && (c.vhl>>4)==4 && header>=20 && header<=p->len && !(c.flags&0x7fff);
#ifdef LAB_TCP_DF
    const bool shouldChange=mutableHeader;
#else
    const bool shouldChange=false;
#endif
    bool valid=sent==ERR_OK && syntheticLength==c.length;
    if (valid && shouldChange) {
      valid=syntheticBytes[6]==0x40 && syntheticBytes[7]==0 && inet_chksum(syntheticBytes,header)==0;
      for (unsigned i=0;i<c.length;++i) {
        if (i!=6 && i!=10 && i!=11 && syntheticBytes[i]!=originalBytes[i])valid=false;
      }
    } else if (valid) valid=memcmp(syntheticBytes,originalBytes,c.length)==0;
    result.pass=valid; pbuf_free(p);
  }
  edgesDone.store(true,std::memory_order_release);
}
#endif

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
#ifdef LAB_PACKET_EDGES
    if (cycle==2 && WiFi.status()==WL_CONNECTED) {
      if (tcpip_callback(runEdges,nullptr)!=ERR_OK) {
        Serial.println("LAB_EDGE_ERROR callback_queue");
      } else {
        const unsigned long deadline=millis();
        while (!edgesDone.load(std::memory_order_acquire) && millis()-deadline<3000) delay(5);
        if (edgesDone.load(std::memory_order_acquire)) {
          for (const auto& r:edgeResults) Serial.printf("LAB_EDGE {\"name\":\"%s\",\"pass\":%s}\n",r.name,r.pass?"true":"false");
        } else Serial.println("LAB_EDGE_ERROR timeout");
      }
    }
#endif
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    delay(200);
    sample("wifi_off", cycle);
  }
  Serial.println("LAB_DONE");
  Serial.flush();
}

void loop() { delay(1000); }
