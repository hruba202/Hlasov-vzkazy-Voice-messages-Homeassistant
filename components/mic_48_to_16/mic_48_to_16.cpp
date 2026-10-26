#include "mic_48_to_16.h"
#include "esphome/core/log.h"
#include <algorithm>

namespace esphome::mic_48_to_16 {
static const char *const TAG = "mic_48_to_16";

void Microphone48To16::setup() {
  output_.reserve(2048);
  source_->add_data_callback([this](const std::vector<uint8_t> &data) { process_(data); });
}

void Microphone48To16::start() {
  if (is_failed()) return;
  if (listeners_++ != 0) return;
  const auto info = source_->get_audio_stream_info();
  if (info.get_sample_rate() != 48000 || info.get_bits_per_sample() != 16 || info.get_channels() != 1) {
    listeners_ = 0;
    ESP_LOGE(TAG, "Expected 48000 Hz mono 16-bit source");
    mark_failed();
    return;
  }
  {
    std::lock_guard<std::mutex> lock(mutex_);
    history_.fill(0);
    position_ = phase_ = 0;
    have_low_byte_ = false;
    enabled_ = true;
  }
  state_ = microphone::STATE_STARTING;
  source_->start();
  ESP_LOGI(TAG, "48 -> 16 kHz microphone started (FIR low-pass)");
}

void Microphone48To16::stop() {
  if (listeners_ == 0 || --listeners_ != 0) return;
  {
    // Finish any in-flight callback before releasing the source listener.
    std::lock_guard<std::mutex> lock(mutex_);
    enabled_ = false;
  }
  source_->stop();
  state_ = microphone::STATE_STOPPING;
}

void Microphone48To16::loop() {
  if (listeners_ != 0 && source_->is_running()) state_ = microphone::STATE_RUNNING;
  if (listeners_ == 0 && state_ != microphone::STATE_STOPPED)
    state_ = microphone::STATE_STOPPED;
}

void Microphone48To16::process_(const std::vector<uint8_t> &data) {
  // Called by the I2S task. No sockets, flash writes or log calls here.
  std::lock_guard<std::mutex> lock(mutex_);
  if (!enabled_) return;
  output_.clear();
  for (const uint8_t byte : data) {
    // Preserve both byte alignment and decimation phase across input chunks.
    if (!have_low_byte_) {
      low_byte_ = byte;
      have_low_byte_ = true;
      continue;
    }
    const int16_t sample = static_cast<int16_t>(static_cast<uint16_t>(low_byte_) | (uint16_t(byte) << 8));
    have_low_byte_ = false;
    history_[position_] = sample;
    position_ = (position_ + 1) % FIR_TAPS;
    if (++phase_ != 3) continue;
    phase_ = 0;
    int64_t accumulator = 0;
    size_t cursor = position_;
    for (size_t tap = 0; tap < FIR_TAPS; ++tap) {
      cursor = cursor == 0 ? FIR_TAPS - 1 : cursor - 1;
      accumulator += static_cast<int32_t>(history_[cursor]) * FIR_COEFFICIENTS[tap];
    }
    const int32_t filtered = static_cast<int32_t>(accumulator / 32768);
    const int16_t result = static_cast<int16_t>(std::clamp(filtered, int32_t(-32768), int32_t(32767)));
    output_.push_back(static_cast<uint16_t>(result) & 0xff);
    output_.push_back(static_cast<uint16_t>(result) >> 8);
  }
  if (!output_.empty()) data_callbacks_.call(output_);
}
}
