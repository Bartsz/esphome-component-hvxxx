#pragma once

#include <string>

#include "esphome/core/component.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/components/i2c/i2c.h"
#include "esphome/components/button/button.h"
#include "esphome/components/template/number/template_number.h"

namespace esphome
{
  namespace hvxxx
  {
    // Forward declaration

    class HVxxxComponent;

    class HVxxxCalibrateButton : public button::Button
    {
    public:
      void set_parent(HVxxxComponent *parent) { parent_ = parent; }

    protected:
      void press_action() override;

      HVxxxComponent *parent_{nullptr};
    };

    class HVxxxComponent : public PollingComponent, public i2c::I2CDevice
    {
    public:
      HVxxxComponent() = default;

      void set_pressure_sensor(sensor::Sensor *pressure) { pressure_sensor_ = pressure; }
      void set_temperature_sensor(sensor::Sensor *temperature) { temperature_sensor_ = temperature; }
      void set_model_text_sensor(text_sensor::TextSensor *model) { model_text_sensor_ = model; }
      void set_serial_text_sensor(text_sensor::TextSensor *serial) { serial_text_sensor_ = serial; }

      // Calibration
      //  zero offset number from TemplateNumber (persistent with restore_value=true)
      void set_offset_number(template_::TemplateNumber *number) { offset_number_ = number; }
      void set_calibrate_button(HVxxxCalibrateButton *button) { calibrate_button_ = button; }

      /// @brief Starts zero pressure offset calibration process
      void calibrate_zero();

      // (from YAML)
      // Mode register (bits configured from YAML in sensor.py)
      void set_user_model_name(const std::string &model) { requested_model_name_ = model; }
      void set_pressure_range_bits(uint8_t bits) { pressure_range_bits_ = bits; }
      void set_pressure_range(float range_in_h2o) { pressure_range_inh2o_ = range_in_h2o; }
      void set_io_watchdog_enabled(bool enabled) { io_watchdog_enabled_ = enabled; }
      void set_bandwidth_mode_bits(uint8_t bits) { bandwidth_limit_bits_ = bits; }
      void set_bandwidth_limit_hz(float limit_hz) { bandwidth_limit_hz_ = limit_hz; }
      void set_notch_filter_enabled(bool enabled) { notch_filter_enabled_ = enabled; }
      void set_rate_control_value(uint8_t value) { rate_control_value_ = value; }

      void setup() override;
      void dump_config() override;
      void update() override;

    protected:
      /// @brief Delay (50 ms) for I2C bus to stabilize on setup. Data sheet specifies maximum of 40ms
      const uint8_t interface_detect_delay_{50};
      /// @brief Delay (180 ms) required for the sensor to settle before first response is valid
      const uint8_t first_response_settling_time_{180};
      /// @brief Flag indicating if communication with the sensor is available
      bool communication_available_{false};
      /// @brief Flag indicating if the sensor is ready to provide valid data
      bool sensor_is_ready_{false};

      sensor::Sensor *pressure_sensor_{nullptr};
      sensor::Sensor *temperature_sensor_{nullptr};
      text_sensor::TextSensor *model_text_sensor_{nullptr};
      text_sensor::TextSensor *serial_text_sensor_{nullptr};
      template_::TemplateNumber *offset_number_{nullptr};
      HVxxxCalibrateButton *calibrate_button_{nullptr};

      // Sensor settings
      uint8_t pressure_range_bits_{0};
      bool io_watchdog_enabled_{false};   // If enabled, chipset monitors I2C communication and resets if no communication within watchdog period equal to Bandwidth time.
      uint8_t bandwidth_limit_bits_{0};   
      bool notch_filter_enabled_{true};
      uint8_t rate_control_value_{0};     // Rate control value for sensor refresh rate. A divider of internal base rate (111Hz) in range 0-255. 0 means automatic selection which is 11 higher then Bandwidth limit.
      float calibration_offset_Pa_{0.0f}; // Calibration offset value in Pa, added to pressure readings. Could be stored as raw value but that would increase complexity.

      // Sensor settings values
      float pressure_range_inh2o_{0.0f};
      float bandwidth_limit_hz_{0.0f}; // 0 means auto selected based on selected pressure range

      bool model_initialized_{false};
      bool serial_initialized_{false};

      std::string requested_model_name_;
      std::string model_name_;
      std::string serial_number_;
      std::string serial_string_;
 
      ///@brief Write 2 bytes of sensor settings (Mode register and Rate register) to the HVxxx sensor over I2C.
      bool write_sensor_settings_();

      ///@brief Read 4 bytes of sensor data (pressure and temperature) from the HVxxx sensor over I2C.
      bool read_sensor_data_(uint8_t *buffer, uint8_t bytes_to_read);
      float parse_pressure_(uint8_t *response_message);
      float parse_temperature_(uint8_t *response_message);
      uint8_t compute_mode_register() const;
      uint8_t compute_rate_register_() const;

      ///@brief Parse the sensor model name and from raw response message and publish to text sensor.
      ///@param response_message Pointer to the raw data buffer containing full sensor responses of 14 bytes (1-2:pressure, 3-4:temperature, 5-10:model, 11-14:serial)
      bool parse_model_name_and_publish_(const uint8_t *response_message);
      ///@brief Parse the sensor serial number and from raw response message and publish to text sensor.
      ///@param response_message Pointer to the raw data buffer containing full sensor responses of 14 bytes (1-2:pressure, 3-4:temperature, 5-10:model, 11-14:serial)
      bool parse_serialno_and_publish_(const uint8_t *response_message);
    };

  } // namespace hvxxx
} // namespace esphome
