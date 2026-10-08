#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <esp_heap_caps.h>

static WebServer server(80);
static constexpr uint32_t CAPS = MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT;
static uint32_t received = 0;
static uint32_t checksum = 2166136261u;
static unsigned uploads = 0, cycle = 0;
static bool restartRequested = false, doneRequested = false;

static void heap(const char* phase) {
  Serial.printf("AP_HEAP {\"phase\":\"%s\",\"cycle\":%u,\"free\":%u,\"largest\":%u,\"minimum\":%u,\"integrity\":%s}\n",
    phase, cycle, heap_caps_get_free_size(CAPS), heap_caps_get_largest_free_block(CAPS),
    heap_caps_get_minimum_free_size(CAPS), heap_caps_check_integrity_all(true) ? "true" : "false");
}

static bool startAp() {
  WiFi.mode(WIFI_AP);
  const bool started = WiFi.softAP("CrossPoint-Lab", nullptr, 1, 0, 2);
  server.begin();
  Serial.printf("AP_READY {\"cycle\":%u,\"started\":%s,\"ip\":\"%s\"}\n",cycle,started?"true":"false",WiFi.softAPIP().toString().c_str());
  heap("active");
  return started;
}

void setup() {
  Serial.begin(115200);
  delay(100);
  heap("baseline");
  server.on("/health", HTTP_GET, []() {
    char body[128];
    snprintf(body,sizeof(body),"{\"cycle\":%u,\"uploads\":%u,\"bytes\":%u,\"fnv32\":%u}",cycle,uploads,received,checksum);
    server.send(200,"application/json",body);
  });
  server.on("/upload", HTTP_POST, []() {
    char body[96];
    snprintf(body,sizeof(body),"{\"bytes\":%u,\"fnv32\":%u}",received,checksum);
    server.send(200,"application/json",body);
    heap("uploaded");
  }, []() {
    auto& upload = server.upload();
    if (upload.status==UPLOAD_FILE_START) {received=0;checksum=2166136261u;}
    else if (upload.status==UPLOAD_FILE_WRITE) {
      for (size_t i=0;i<upload.currentSize;++i) checksum=(checksum^upload.buf[i])*16777619u;
      received+=upload.currentSize;
    } else if (upload.status==UPLOAD_FILE_END) {
      ++uploads;
      Serial.printf("AP_UPLOAD {\"cycle\":%u,\"bytes\":%u,\"fnv32\":%u}\n",cycle,received,checksum);
    }
  });
  server.on("/restart", HTTP_POST, []() {server.send(200,"text/plain","restart");restartRequested=true;});
  server.on("/done", HTTP_POST, []() {server.send(200,"text/plain","done");doneRequested=true;});
  startAp();
}

void loop() {
  server.handleClient();
  if (restartRequested || doneRequested) {
    // Finish the HTTP response before dropping the actual guest AP/netif.
    delay(100);
    server.stop();
    WiFi.softAPdisconnect(true);
    WiFi.mode(WIFI_OFF);
    delay(200);
    heap("off");
    if (doneRequested) {Serial.println("LAB_DONE");Serial.flush();doneRequested=false;while(true)delay(1000);}
    restartRequested=false;
    ++cycle;
    startAp();
  }
  delay(1);
}
