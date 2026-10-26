#pragma once
#include "esphome/core/component.h"
#include "esphome/components/microphone/microphone.h"
#include "fir_coefficients.h"
#include <array>
#include <mutex>

namespace esphome::mic_48_to_16 {
class Microphone48To16 : public microphone::Microphone, public Component {
 public:
  Microphone48To16() { audio_stream_info_ = audio::AudioStreamInfo(16, 1, 16000); }
  void set_source(microphone::Microphone *source) { source_ = source; }
  void setup() override;
  void loop() override;
  void start() override;
  void stop() override;
 protected:
  void process_(const std::vector<uint8_t> &data);
  microphone::Microphone *source_{nullptr};
  std::mutex mutex_;
  bool enabled_{false};
  unsigned listeners_{0};  // All start/stop calls come from the ESPHome loop.
  std::array<int16_t, FIR_TAPS> history_{};
  size_t position_{0};
  unsigned phase_{0};
  bool have_low_byte_{false};
  uint8_t low_byte_{0};
  std::vector<uint8_t> output_;
};
}
