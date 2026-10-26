#include "huskylens_bridge.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"

namespace esphome {
namespace huskylens_bridge {
static const char *const TAG = "huskylens_bridge";

void HuskyLensBridge::dump_config() {
  ESP_LOGCONFIG(TAG, "HuskyLens V1: first block, poll interval configured below");
  LOG_I2C_DEVICE(this);
  LOG_UPDATE_INTERVAL(this);
}

void HuskyLensBridge::update() {
  if (busy_)
    return;
  // REQUEST_BLOCKS: geometry refers to blocks, never line-arrow endpoints.
  const uint8_t request[] = {0x55, 0xAA, 0x11, 0x00, 0x21, 0x31};
  frame_pos_ = 0;
  frame_size_ = 0;
  remaining_ = 0;
  have_info_ = false;
  pending_detected_ = false;
  if (this->write(request, sizeof(request)) != i2c::ERROR_OK) {
    fail_();
    return;
  }
  started_ = last_read_ = millis();
  busy_ = true;
}

void HuskyLensBridge::loop() {
  if (!busy_)
    return;
  const uint32_t now = millis();
  if (now - started_ >= 150) {
    fail_();
    return;
  }
  if (now - last_read_ < 5)
    return;
  last_read_ = now;
  // Same 16-byte stream reads as the manufacturer's V1 I2C transport.
  uint8_t chunk[16];
  if (this->read(chunk, sizeof(chunk)) != i2c::ERROR_OK) {
    fail_();
    return;
  }
  for (uint8_t byte : chunk) {
    if (!busy_)
      break;
    consume_(byte);
  }
}

void HuskyLensBridge::consume_(uint8_t byte) {
  if (frame_pos_ == 0) {
    if (byte == 0x55)
      frame_buffer_[frame_pos_++] = byte;
    return;
  }
  if (frame_pos_ == 1 && byte != 0xAA) {
    frame_pos_ = byte == 0x55 ? 1 : 0;
    return;
  }
  frame_buffer_[frame_pos_++] = byte;
  if (frame_pos_ == 4) {
    frame_size_ = static_cast<size_t>(byte) + 6;
    if (frame_size_ > sizeof(frame_buffer_)) {
      fail_();
      return;
    }
  }
  if (frame_pos_ < 4 || frame_pos_ != frame_size_)
    return;
  uint8_t sum = 0;
  for (size_t i = 0; i + 1 < frame_size_; i++)
    sum += frame_buffer_[i];
  if (sum != byte) {
    fail_();
    return;
  }
  frame_();
  frame_pos_ = 0;
}

void HuskyLensBridge::frame_() {
  const uint8_t command = frame_buffer_[4];
  const uint8_t length = frame_buffer_[3];
  auto word = [this](size_t offset) -> uint16_t {
    return static_cast<uint16_t>(frame_buffer_[offset]) |
           (static_cast<uint16_t>(frame_buffer_[offset + 1]) << 8);
  };
  if (!have_info_) {
    if (command != 0x29 || length != 10) {
      fail_();
      return;
    }
    remaining_ = word(5);
    if (remaining_ > 64) {
      fail_();
      return;
    }
    have_info_ = true;
    if (remaining_ == 0)
      finish_();
    return;
  }
  if (command != 0x2A || length != 10 || remaining_ == 0) {
    fail_();
    return;
  }
  if (!pending_detected_) {
    pending_[0] = word(13);  // ID
    pending_[1] = word(5);   // center X
    pending_[2] = word(7);   // center Y
    pending_[3] = word(9);   // width
    pending_[4] = word(11);  // height
    pending_[5] = command;
    pending_detected_ = true;
  }
  if (--remaining_ == 0)
    finish_();
}

void HuskyLensBridge::finish_() {
  for (size_t i = 0; i < 6; i++)
    values_[i] = pending_[i];
  detected_ = pending_detected_;
  valid_ = true;
  busy_ = false;
  status_clear_warning();
}

void HuskyLensBridge::fail_() {
  // Retry on the next poll; never call setup() or mark_failed() repeatedly.
  valid_ = false;
  detected_ = false;
  busy_ = false;
  frame_pos_ = 0;
  status_set_warning();
}
}  // namespace huskylens_bridge
}  // namespace esphome
