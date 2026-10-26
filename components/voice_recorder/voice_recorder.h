#pragma once
#include "esphome/core/component.h"
#include "esphome/components/microphone/microphone.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include <atomic>
#include <mutex>
#include <string>

namespace esphome::voice_recorder {
class VoiceRecorder : public Component {
 public:
  void set_microphone(microphone::Microphone *mic) { mic_ = mic; }
  void set_status_sensor(text_sensor::TextSensor *sensor) { status_ = sensor; }
  void set_receiver(const std::string &ip, uint16_t port, const std::string &token) {
    url_ = "http://" + ip + ":" + std::to_string(port) + "/recordings";
    auth_ = "Bearer " + token;
  }
  void setup() override;
  void loop() override;
  void record();
  void cancel();
  bool busy() const { return state_ != State::IDLE; }
 protected:
  enum class State { IDLE, CAPTURE, UPLOAD };
  static constexpr size_t PCM_BYTES = 48000 * 2 * 10;
  static void upload_task_(void *arg);
  void publish_(const char *message);
  void stop_capture_();
  microphone::Microphone *mic_{nullptr};
  text_sensor::TextSensor *status_{nullptr};
  uint8_t *buffer_{nullptr};
  std::mutex mutex_;
  size_t used_{0};
  bool accepting_{false};
  bool owns_mic_{false};
  State state_{State::IDLE};
  uint32_t started_{0};
  std::atomic<int> upload_result_{0};
  std::string url_, auth_;
};
}  // namespace esphome::voice_recorder
