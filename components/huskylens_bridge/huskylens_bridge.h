#pragma once

#include <cmath>
#include "esphome/core/component.h"
#include "esphome/components/i2c/i2c.h"

namespace esphome {
namespace huskylens_bridge {

// Original HuskyLens V1 protocol, not HuskyLens V2.
class HuskyLensBridge : public PollingComponent, public i2c::I2CDevice {
 public:
  void update() override;
  void loop() override;
  void dump_config() override;
  float get_setup_priority() const override { return setup_priority::DATA; }
  bool valid() const { return valid_; }
  bool detected() const { return valid_ && detected_; }
  float value(size_t index) const {
    return valid_ && detected_ && index < 6 ? values_[index] : NAN;
  }

 protected:
  void consume_(uint8_t byte);
  void frame_();
  void fail_();
  void finish_();
  uint8_t frame_buffer_[32]{};
  size_t frame_pos_{0};
  size_t frame_size_{0};
  uint16_t remaining_{0};
  bool have_info_{false};
  bool busy_{false};
  bool valid_{false};
  bool detected_{false};
  bool pending_detected_{false};
  float values_[6]{};
  float pending_[6]{};
  uint32_t started_{0};
  uint32_t last_read_{0};
};

}  // namespace huskylens_bridge
}  // namespace esphome
