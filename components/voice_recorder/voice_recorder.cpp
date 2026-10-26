#include "voice_recorder.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"
#include "esp_heap_caps.h"
#include "esp_http_client.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <algorithm>
#include <cstring>

namespace esphome::voice_recorder {
static const char *const TAG = "voice_recorder";

void VoiceRecorder::publish_(const char *message) {
  status_->publish_state(message);
  ESP_LOGI(TAG, "D2: %s", message);
}

void VoiceRecorder::setup() {
  // Permanent PSRAM storage avoids freeing memory while the microphone callback runs.
  buffer_ = static_cast<uint8_t *>(heap_caps_malloc(PCM_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (buffer_ == nullptr) {
    publish_("Chyba: nedostatek PSRAM");
    mark_failed();
    return;
  }
  mic_->add_data_callback([this](const std::vector<uint8_t> &data) {
    // Runs in the microphone task: only bounded memory copies, never networking or logging.
    std::lock_guard<std::mutex> lock(mutex_);
    if (!accepting_) return;
    const size_t count = std::min(data.size(), PCM_BYTES - used_);
    std::memcpy(buffer_ + used_, data.data(), count);
    used_ += count;
    if (used_ == PCM_BYTES) accepting_ = false;
  });
  publish_("Pripraveno");
}

void VoiceRecorder::record() {
  if (is_failed() || busy() || !mic_->is_stopped()) {
    ESP_LOGW(TAG, "D2: recording refused: busy, microphone active or component failed");
    return;
  }
  const auto info = mic_->get_audio_stream_info();
  if (info.get_sample_rate() != 48000 || info.get_bits_per_sample() != 16 || info.get_channels() != 1) {
    publish_("Chyba: format musi byt mono 48000 Hz 16 bit");
    return;
  }
  {
    std::lock_guard<std::mutex> lock(mutex_);
    used_ = 0;
    accepting_ = true;
  }
  owns_mic_ = true;
  state_ = State::CAPTURE;
  started_ = millis();
  mic_->start();
  publish_("Nahravam 10 s");
}

void VoiceRecorder::stop_capture_() {
  {
    std::lock_guard<std::mutex> lock(mutex_);
    accepting_ = false;
  }
  if (owns_mic_) {
    mic_->stop();
    owns_mic_ = false;
  }
}

void VoiceRecorder::cancel() {
  if (state_ == State::CAPTURE) {
    stop_capture_();
    state_ = State::IDLE;
    publish_("Zruseno bez ulozeni");
  } else if (state_ == State::UPLOAD) {
    ESP_LOGW(TAG, "D2: upload already in progress; wait for its result");
  }
}

void VoiceRecorder::loop() {
  if (state_ == State::CAPTURE) {
    size_t count;
    {
      std::lock_guard<std::mutex> lock(mutex_);
      count = used_;
    }
    if (count == PCM_BYTES) {
      stop_capture_();
      state_ = State::UPLOAD;
      upload_result_.store(0);
      publish_("Odesilam do HA");
      // Socket waits are isolated from the ESPHome loop and USB camera callbacks.
      if (xTaskCreate(upload_task_, "voice_upload", 8192, this, 2, nullptr) != pdPASS) {
        state_ = State::IDLE;
        publish_("Chyba: nelze spustit prenos");
      }
    } else if (millis() - started_ > 15000) {
      stop_capture_();
      state_ = State::IDLE;
      publish_("Chyba: nekompletni zvuk do 15 s");
    }
  } else if (state_ == State::UPLOAD) {
    const int result = upload_result_.load();
    if (result == 0) return;
    state_ = State::IDLE;
    if (result == 201) {
      publish_("Ulozeno v HA");
    } else {
      ESP_LOGW(TAG, "D2: upload failed, HTTP result %d (negative = transport error)", result);
      publish_("Chyba prenosu: overte log prijimace");
    }
  }
}

void VoiceRecorder::upload_task_(void *arg) {
  auto *self = static_cast<VoiceRecorder *>(arg);
  esp_http_client_config_t config{};
  config.url = self->url_.c_str();
  config.method = HTTP_METHOD_POST;
  config.timeout_ms = 10000;
  config.disable_auto_redirect = true;
  esp_http_client_handle_t client = esp_http_client_init(&config);
  int result = -1;
  if (client != nullptr) {
    esp_http_client_set_header(client, "Authorization", self->auth_.c_str());
    esp_http_client_set_header(client, "Content-Type", "application/octet-stream");
    esp_http_client_set_post_field(client, reinterpret_cast<const char *>(self->buffer_), PCM_BYTES);
    if (esp_http_client_perform(client) == ESP_OK)
      result = esp_http_client_get_status_code(client);
    esp_http_client_cleanup(client);
  }
  // No access to the PCM buffer after publishing completion; main loop may reuse it.
  self->upload_result_.store(result == 0 ? -1 : result);
  vTaskDelete(nullptr);
}
}  // namespace esphome::voice_recorder
