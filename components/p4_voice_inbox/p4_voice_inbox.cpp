#include "p4_voice_inbox.h"
#include "esphome/core/hal.h"
#include "esphome/core/log.h"
#include "esp_heap_caps.h"
#include "esp_http_client.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <algorithm>
#include <cstring>

namespace esphome::p4_voice_inbox {
static const char *const TAG = "p4_voice_inbox";

void P4VoiceInbox::publish_(const char *message) {
  status_->publish_state(message);
  ESP_LOGI(TAG, "D5: %s", message);
}

void P4VoiceInbox::setup() {
  // One permanent PSRAM allocation; callback and uploader never see freed memory.
  buffer_ = static_cast<uint8_t *>(heap_caps_malloc(PCM_BYTES, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (buffer_ == nullptr) {
    publish_("Chyba: nedostatek PSRAM");
    mark_failed();
    return;
  }
  mic_->add_data_callback([this](const std::vector<uint8_t> &data) {
    // Audio task: bounded copies only, no I/O, logging, networking or allocation.
    std::lock_guard<std::mutex> lock(mutex_);
    if (!accepting_) return;
    const size_t count = std::min(data.size(), PCM_BYTES - used_) & ~size_t(1);
    if (count) std::memcpy(buffer_ + used_, data.data(), count);
    used_ += count;
    if (used_ == PCM_BYTES) accepting_ = false;
  });
  ESP_LOGI(TAG, "D5: buffer %u B in PSRAM, mono 48000 Hz / 16 bit, max 10 s", unsigned(PCM_BYTES));
  publish_("Pripraveno");
}

void P4VoiceInbox::record() {
  if (busy()) return;  // Preserve an ongoing capture/upload's visible status.
  if (is_failed() || mic_->is_failed()) { publish_("Chyba: mikrofon nebo rekorder neni pripraven"); return; }
  if (!phone_->is_idle()) { publish_("Nelze nahravat: probiha volani"); return; }
  if (mic_->get_mute_state()) { publish_("Nelze nahravat: mikrofon je ztlumeny"); return; }
  if (!mic_->is_stopped()) { publish_("Mikrofon je zaneprazdneny, zkuste znovu"); return; }
  const auto info = mic_->get_audio_stream_info();
  if (info.get_sample_rate() != 48000 || info.get_bits_per_sample() != 16 || info.get_channels() != 1) {
    publish_("Chyba: ocekavano mono 48000 Hz / 16 bit");
    return;
  }
  {
    std::lock_guard<std::mutex> lock(mutex_);
    used_ = 0;
    accepting_ = true;
  }
  // This pinned Audio Stack reference-counts start/stop. Release only our listener.
  mic_->start();
  owns_listener_ = true;
  state_ = State::CAPTURE;
  started_ = millis();
  publish_("Nahravam, nejvyse 10 s");
}

void P4VoiceInbox::stop_capture_() {
  {
    std::lock_guard<std::mutex> lock(mutex_);
    accepting_ = false;
  }
  if (owns_listener_) {
    mic_->stop();
    owns_listener_ = false;
  }
}

void P4VoiceInbox::discard_(const char *message) {
  stop_capture_();
  state_ = State::IDLE;
  publish_(message);
}

void P4VoiceInbox::cancel() {
  if (state_ == State::CAPTURE) discard_("Zruseno bez ulozeni");
  else if (state_ == State::UPLOAD) ESP_LOGI(TAG, "D5: upload already started; wait for confirmation");
}

void P4VoiceInbox::save() {
  if (state_ != State::CAPTURE) return;
  if (!phone_->is_idle()) { discard_("Zruseno: hovor ma prednost"); return; }
  stop_capture_();
  // stop_capture_ synchronizes with the callback; used_ and buffer stay immutable during upload.
  upload_bytes_ = used_;
  if (upload_bytes_ < 48000) {
    state_ = State::IDLE;
    publish_("Vzkaz je prilis kratky (minimum 0,5 s)");
    return;
  }
  state_ = State::UPLOAD;
  upload_result_.store(0);
  publish_("Odesilam do HA");
  ESP_LOGI(TAG, "D5: sending %u PCM bytes (%.1f s)", unsigned(upload_bytes_), upload_bytes_ / 96000.0f);
  if (xTaskCreate(upload_task_, "inbox_upload", 8192, this, 1, nullptr) != pdPASS) {
    state_ = State::IDLE;
    publish_("Chyba: nelze spustit prenos");
  }
}

void P4VoiceInbox::loop() {
  if (state_ == State::CAPTURE) {
    if (!phone_->is_idle()) { discard_("Zruseno: hovor ma prednost"); return; }
    if (mic_->get_mute_state()) { discard_("Zruseno: mikrofon byl ztlumen"); return; }
    size_t count;
    { std::lock_guard<std::mutex> lock(mutex_); count = used_; }
    if (count == PCM_BYTES) save();
    else if (millis() - started_ > 15000) discard_("Chyba: mikrofon nedodal zvuk vcas");
  } else if (state_ == State::UPLOAD) {
    const int result = upload_result_.load();
    if (result == 0) return;
    state_ = State::IDLE;
    ESP_LOGI(TAG, "D5: upload HTTP result %d (negative = transport error)", result);
    switch (result) {
      case 201: publish_("Ulozeno v HA"); break;
      case 401: publish_("HTTP 401: overte zdroj, klic a povolenou sit v HA"); break;
      case 400: publish_("HTTP 400: prijimac odmitl format pozadavku"); break;
      case 413: publish_("HTTP 413: vzkaz prekrocil limit"); break;
      case 415: publish_("HTTP 415: nepodporovany zvukovy format"); break;
      case 503: publish_("HTTP 503: prijimac nedostupny nebo blokace; pockejte 60 s"); break;
      case 507: publish_("HTTP 507: plna schranka nebo disk HA"); break;
      default: publish_("Ulozeni nepotvrzeno: overte HA a sit pred novym pokusem"); break;
    }
  }
}

void P4VoiceInbox::upload_task_(void *arg) {
  auto *self = static_cast<P4VoiceInbox *>(arg);
  esp_http_client_config_t config{};
  config.url = self->url_.c_str();
  config.method = HTTP_METHOD_POST;
  config.timeout_ms = 15000;
  config.disable_auto_redirect = true;
  esp_http_client_handle_t client = esp_http_client_init(&config);
  int result = -1;
  if (client != nullptr) {
    esp_http_client_set_header(client, "X-Voice-Source", self->source_.c_str());
    esp_http_client_set_header(client, "X-Voice-Key", self->key_.c_str());
    esp_http_client_set_header(client, "Content-Type", "application/octet-stream");
    esp_http_client_set_header(client, "X-Audio-Rate", "48000");
    esp_http_client_set_header(client, "X-Audio-Bits", "16");
    esp_http_client_set_header(client, "X-Audio-Channels", "1");
    esp_http_client_set_post_field(client, reinterpret_cast<const char *>(self->buffer_), self->upload_bytes_);
    if (esp_http_client_perform(client) == ESP_OK) result = esp_http_client_get_status_code(client);
    esp_http_client_cleanup(client);
  }
  // Release publication: main loop can reuse the PCM buffer only after all client I/O ended.
  // No automatic retries: the server may have committed even if its response was lost.
  self->upload_result_.store(result == 0 ? -1 : result);
  vTaskDelete(nullptr);
}
}  // namespace esphome::p4_voice_inbox
