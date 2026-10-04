#pragma once
#include <Arduino.h>
#define LOG_ERR(module, fmt, ...) Serial.printf("LAB_PR_ERROR " fmt "\n", ##__VA_ARGS__)
#define LOG_INF(module, fmt, ...) Serial.printf("LAB_PR_INFO " fmt "\n", ##__VA_ARGS__)
