#include <Arduino.h>
#include <BitmapHelpers.h>
#include <esp_heap_caps.h>

// The external tone adjustment is fixed to identity in this dither-only probe.
int adjustPixel(int gray) { return gray; }

static constexpr uint32_t CAPS = MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT;
static void* pressure[256]{};

static void sample(const char* name) {
  Serial.printf("IMAGE_HEAP {\"phase\":\"%s\",\"free\":%u,\"largest\":%u,\"integrity\":%s}\n",
                name, heap_caps_get_free_size(CAPS), heap_caps_get_largest_free_block(CAPS),
                heap_caps_check_integrity_all(true) ? "true" : "false");
}

template <class Ditherer>
static void exercise(const char* name, bool fragmented) {
  const size_t before = heap_caps_get_free_size(CAPS);
  uint32_t hash = 2166136261u;
  bool valid;
  size_t retained;
  {
    Ditherer ditherer(800);
    valid = ditherer.isValid();
    retained = before - heap_caps_get_free_size(CAPS);
    // Production callers check validity. Never dereference a failed base buffer.
    if (valid) {
      for (int y = 0; y < 32; ++y) {
        for (int x = 0; x < 800; ++x) {
          hash = (hash ^ ditherer.processPixel((x * 13 + y * 7) & 255, x)) * 16777619u;
        }
        ditherer.nextRow();
      }
      ditherer.reset();
    }
  }
  Serial.printf("IMAGE_CASE {\"name\":\"%s\",\"fragmented\":%s,\"valid\":%s,\"retained\":%u,\"hash\":%u,\"recovered\":%s}\n",
                name, fragmented ? "true" : "false", valid ? "true" : "false", unsigned(retained), hash,
                before == heap_caps_get_free_size(CAPS) ? "true" : "false");
}

void setup() {
  Serial.begin(115200);
  delay(100);
  sample("before_oom_warmup");
  // Prime the runtime's first allocation-failure path before cleanup comparisons.
  // This deliberately exceeds the C3 heap and is never a production allocation.
  void* failed = ::operator new(16 * 1024 * 1024, std::nothrow);
  ::operator delete(failed);
  sample("baseline");
  exercise<Atkinson1BitDitherer>("atkinson1", false);
  exercise<AtkinsonDitherer>("atkinson2", false);
  exercise<FloydSteinbergDitherer>("floyd", false);
  sample("normal_released");
  // Deliberate fallible allocation creates separated holes in the real C3 heap.
  // Fixed static pointer metadata avoids an allocation inside the allocator test.
  unsigned count = 0;
  for (auto& p : pressure) {
    p = heap_caps_malloc(2048, CAPS);
    if (!p) break;
    ++count;
  }
  for (unsigned i = 0; i < count; i += 2) {
    heap_caps_free(pressure[i]);
    pressure[i] = nullptr;
  }
  Serial.printf("IMAGE_PRESSURE %u\n", count);
  sample("holes");
  exercise<Atkinson1BitDitherer>("atkinson1", true);
  exercise<AtkinsonDitherer>("atkinson2", true);
  exercise<FloydSteinbergDitherer>("floyd", true);
  sample("holes_released");
  for (auto& p : pressure) {
    heap_caps_free(p);
    p = nullptr;
  }
  sample("all_released");
  Serial.println("LAB_DONE");
  Serial.flush();
}

void loop() { delay(1000); }
