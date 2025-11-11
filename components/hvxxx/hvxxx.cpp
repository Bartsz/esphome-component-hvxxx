#include "hvxxx.h"

#include "esphome/core/log.h"

#include <algorithm>
#include <cstdio>
#include <cstdint>
#include <cmath>
#include <limits>

namespace esphome
{
  namespace hvxxx
  {

    static const char *const TAG = "hvxxx";

    void HVxxxComponent::setup()
    { 
      set_timeout(this->first_response_settling_time_ - this->interface_detect_delay_, [this]()
                  { this->sensor_is_ready_ = true; });

      set_timeout(this->interface_detect_delay_, [this]()
                  {
                    this->communication_available_ = true;

                    ESP_LOGCONFIG(TAG, "Setting up HVxxx pressure sensor...");
                    if (!this->write_sensor_settings_())
                    {
                      ESP_LOGE(TAG, "Failed to write sensor settings during setup");
                      this->mark_failed("I2C communication failed when writing settings during setup");
                    }

                    uint8_t buffer[14] = {0};
                    if (this->read_sensor_data_(buffer, sizeof(buffer)))
                    {
                      this->model_initialized_ = this->parse_model_name_and_publish_(buffer);
                      this->serial_initialized_ = this->parse_serialno_and_publish_(buffer);
                    }
                    else
                    {
                      this->model_initialized_ = false;
                      this->serial_initialized_ = false;
                    }
                    if (!this->model_initialized_ || !this->serial_initialized_)
                    {
                      this->mark_failed("I2C communication failed when reading model and serial during setup");
                    } });

      if (this->offset_number_ != nullptr && this->offset_number_->has_state())
      {
        this->calibration_offset_Pa_ = this->offset_number_->state;
        ESP_LOGCONFIG(TAG, "Restored calibration offset: %.3f Pa", this->calibration_offset_Pa_);
      }
    }

    void HVxxxComponent::dump_config()
    {
      ESP_LOGCONFIG(TAG, "HVxxx pressure sensor:");
      LOG_I2C_DEVICE(this);
      LOG_UPDATE_INTERVAL(this);

      ESP_LOGCONFIG(TAG, "  Pressure range: %.3f inH2O", this->pressure_range_inh2o_);

      if (this->model_initialized_)
      {
        ESP_LOGCONFIG(TAG, "  Model: %s", this->model_name_.c_str());
      }
      if (this->serial_initialized_)
      {
        ESP_LOGCONFIG(TAG, " Serial: %s", this->serial_string_.c_str());
      }

      LOG_SENSOR("  Pressure: ", this->pressure_sensor_);
      LOG_SENSOR("  Temperature: ", this->temperature_sensor_);
      LOG_TEXT_SENSOR("  Model text: ", this->model_text_sensor_);
      LOG_TEXT_SENSOR(" Serial text: ", this->serial_text_sensor_);
    }

    void HVxxxComponent::update()
    {
      if (!this->sensor_is_ready_)
      {
        ESP_LOGW(TAG, "Sensor not ready yet; skipping update");
        this->status_set_warning("Waiting for sensor to be ready");
        return;
      }

      uint8_t buffer[4] = {0};
      if (this->read_sensor_data_(buffer, sizeof(buffer)))
      {
        float pressure_Pa = this->parse_pressure_(buffer);
        if (!std::isnan(pressure_Pa))
          this->pressure_sensor_->publish_state(pressure_Pa + this->calibration_offset_Pa_);

        float temperature_C = this->parse_temperature_(buffer);
        if (!std::isnan(temperature_C))
          this->temperature_sensor_->publish_state(temperature_C);

        this->status_clear_warning();
      }
      else
      {
        this->status_set_warning("communication failed");
      }
    }

    void HVxxxCalibrateButton::press_action()
    {
      if (this->parent_ != nullptr)
        this->parent_->calibrate_zero();
    }

    void HVxxxComponent::calibrate_zero()
    {
      uint8_t buffer[2] = {0};
      this->read_sensor_data_(buffer, 2);
      float pressure_Pa = this->parse_pressure_(buffer);
      if (!std::isnan(pressure_Pa))
        this->calibration_offset_Pa_ = -pressure_Pa;

      if (this->offset_number_ != nullptr)
      {
        this->offset_number_->publish_state(this->calibration_offset_Pa_);
      }
    }

    bool HVxxxComponent::read_sensor_data_(uint8_t *buffer, uint8_t bytes_to_read)
    {
      if (this->read(buffer, bytes_to_read) != i2c::ERROR_OK)
      {
        ESP_LOGW(TAG, "I2C read failed");
        return false;
      }

      return true;
    }

    bool HVxxxComponent::write_sensor_settings_()
    {
      uint8_t cmd[2];
      cmd[0] = this->compute_mode_register();
      cmd[1] = this->compute_rate_register_();

      // Datasheet requirement: When using SPI, Mode and Rate bytes must be sent on each data read cycle.
      if (this->write(cmd, sizeof(cmd)) != i2c::ERROR_OK)
      {
        ESP_LOGW(TAG, "I2C write failed");
        return false;
      }

      return true;
    }

    uint8_t HVxxxComponent::compute_mode_register() const
    {
      uint8_t mode = 0;
      mode = this->pressure_range_bits_ & 0x07;           // Bits 0-3: Pressure Range
      mode |= (this->io_watchdog_enabled_ ? 1 << 4 : 0);  // Bit 4: I/O Watchdog
      mode |= (this->bandwidth_limit_bits_ & 0x03) << 5;  // Bits 5-6: Bandwidth Limit
      mode |= (this->notch_filter_enabled_ ? 1 << 7 : 0); // Bit 7: Notch Filter Enable

      return mode;
    }

    uint8_t HVxxxComponent::compute_rate_register_() const
    {
      // Internal data rate is 111 Hz; Rate Control register is the divisor.
      constexpr float INTERNAL_RATE_HZ = 111.0f;

      const uint32_t interval_ms = this->get_update_interval();
      if (interval_ms == 0u)
      {
        return 0u; // Use automatic setting if no interval is defined
      }

      const float interval_s = interval_ms / 1000.0f;
      if (interval_s <= 0.0f)
      {
        return 0u;
      }

      const float desired_rate_hz = 1.0f / interval_s;
      if (desired_rate_hz <= 0.0f)
      {
        return 0u;
      }

      float divisor = INTERNAL_RATE_HZ / desired_rate_hz;
      divisor = std::clamp(divisor, 1.0f, 255.0f);

      // Round to nearest integer
      return static_cast<uint8_t>(divisor + 0.5f);
    }

    float HVxxxComponent::parse_pressure_(uint8_t *response_message)
    {
      if (this->pressure_sensor_ == nullptr || this->pressure_range_inh2o_ <= 0.0f)
      {
        return std::numeric_limits<float>::quiet_NaN();
      }

      // Raw pressure (signed 16-bit)
      int16_t raw_pressure = static_cast<int16_t>((static_cast<uint16_t>(response_message[0]) << 8) | response_message[1]);

      // Compute and publish pressure (in Pascals)
      const float counts = static_cast<float>(raw_pressure);
      const float denominator = 0.9f * 32768.0f;                                       // Denominator =  0.9 * 2^15 - sensor uses 90% of full scale
      const float pressure_inh2o = counts / denominator * this->pressure_range_inh2o_; // Pressure detected by sensor in inH2O = digital_value / Denominator * Pressure_Range_Selected
      const float pressure_pa = pressure_inh2o * 248.84f;                              // Pressure converted to Pascals = pressure_inh2o * 248.84 (Pa per inH2O)

      return pressure_pa;
    }

    float HVxxxComponent::parse_temperature_(uint8_t *response_message)
    {
      bool read_temperature = this->temperature_sensor_ != nullptr;
      if (!read_temperature)
      {
        return std::numeric_limits<float>::quiet_NaN();
      }

      // Compute and publish temperature (°C) – 8.8 fixed point
      int16_t raw_temperature = ((static_cast<int16_t>(response_message[2]) << 8) | response_message[3]); // Raw temperature (signed 8.8 fixed-point)
      const float temperature_c = static_cast<float>(raw_temperature) / 256.0f;                           // Convert to °C MSB as integer, LSB as fraction

      return temperature_c;
    }

    bool HVxxxComponent::parse_model_name_and_publish_(const uint8_t *response_message)
    {
      if (this->model_text_sensor_ == nullptr)
        return true;

      const uint8_t *model_bytes = &response_message[4]; // model starts at byte 5, length 6
      if (model_bytes[5] != 0)
      {
        ESP_LOGW(TAG, "Model string is not null-terminated as expected");
        return false;
      }

      // Construct string from the first 5 bytes of data, which may not be null-terminated.
      this->model_name_.assign(reinterpret_cast<const char *>(model_bytes), 5);
      bool user_model_match = (this->model_name_ == this->requested_model_name_);
      if (!user_model_match)
      {
        ESP_LOGE(TAG, "Sensor model mismatch: expected '%s', got '%s'. Please check wiring, I2C address, YAML configuration file and sensor.",
                 this->requested_model_name_.c_str(), this->model_name_.c_str());
        this->mark_failed("Sensor model mismatch");
        return false;
      }
      this->model_text_sensor_->publish_state(this->model_name_);
      return true;
    }

    bool HVxxxComponent::parse_serialno_and_publish_(const uint8_t *response_message)
    {
      if (this->serial_text_sensor_ == nullptr)
        return true;

      const uint8_t *serial_number_bytes = &response_message[10]; // Serial number starts at byte 11, length 4
      uint32_t serial_number = 0;

      for (size_t i = 0; i < 4; ++i)
      {
        serial_number = (serial_number << 8) | serial_number_bytes[i];
      }

      char buf[9];
      std::snprintf(buf, sizeof(buf), "%08X", serial_number);
      this->serial_string_.assign(buf);
      this->serial_text_sensor_->publish_state(this->serial_string_);
      return true;
    }

  } // namespace hvxxx
} // namespace esphome
