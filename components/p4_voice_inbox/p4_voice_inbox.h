#pragma once
#include "esphome/core/component.h"
#include "esphome/components/esp_audio_stack/microphone/esp_audio_stack_microphone.h"
#include "esphome/components/voip_stack/voip_stack.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include <atomic>
#include <mutex>
#include <string>

namespace esphome::p4_voice_inbox {
class P4VoiceInbox : public Component {
 public:
  void set_microphone(esp_audio_stack::ESPAudioStackMicrophone *mic) { mic_ = mic; }
  void set_phone(voip_stack::VoipStack *phone) { phone_ = phone; }
  void set_status_sensor(text_sensor::TextSensor *status) { status_ = status; }
  void set_receiver(const std::string &ip, uint16_t port, const std::string &source, const std::string &key) {
    url_ = "http://" + ip + ":" + std::to_string(port) + "/api/voice_inbox/upload";
    source_ = source;
    key_ = key;
  }
  float get_setup_priority() const override { return setup_priority::AFTER_CONNECTION; }
  void setup() override;
  void loop() override;
  void record();
  void save();
  void cancel();
  bool busy() const { return state_ != State::IDLE; }
  bool recording() const { return state_ == State::CAPTURE; }
  bool can_record() const { return !is_failed() && !busy() && phone_->is_idle(); }

 protected:
  enum class State { IDLE, CAPTURE, UPLOAD };
  static constexpr size_t PCM_BYTES = 48000 * 2 * 10;
  static void upload_task_(void *arg);
  void publish_(const char *message);
  void stop_capture_();
  void discard_(const char *message);
  esp_audio_stack::ESPAudioStackMicrophone *mic_{nullptr};
  voip_stack::VoipStack *phone_{nullptr};
  text_sensor::TextSensor *status_{nullptr};
  uint8_t *buffer_{nullptr};
  std::mutex mutex_;
  size_t used_{0};
  size_t upload_bytes_{0};
  bool accepting_{false};
  bool owns_listener_{false};
  State state_{State::IDLE};
  uint32_t started_{0};
  std::atomic<int> upload_result_{0};
  std::string url_, source_, key_;
};
}  // namespace esphome::p4_voice_inbox
