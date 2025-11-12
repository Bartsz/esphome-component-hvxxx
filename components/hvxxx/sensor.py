"""
HVxxx differential pressure sensor platform for ESPHome.
Supports HV110, HV120, HV160, HV210 chip models from Superior SENSOR TECHNOLOGY.
Features:
- Pressure + optional temperature sensors
- Calibration offset number (persistent)
- Calibration button
"""

from logging import config
import esphome.codegen as cg
import esphome.config_validation as cv

from esphome.components import i2c, sensor, text_sensor, number, button
from esphome.const import (
    CONF_ID,
    CONF_NAME,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    STATE_CLASS_MEASUREMENT,
    UNIT_CELSIUS,
    UNIT_PASCAL,
    ICON_GAUGE,
    ICON_THERMOMETER,
    ENTITY_CATEGORY_CONFIG,
)

from .sensor_parameters import (
    PRESSURE_RANGE_TO_BITS,
    MODEL_OPTIONS,
    PRESSURE_RANGE_OPTIONS,
    BANDWIDTH_MODES,
)

DEPENDENCIES = ["i2c"]

AUTO_LOAD = [
    "i2c",
    "sensor",
    "text_sensor",
    "number",
    "button",
]

hvxxx_ns = cg.esphome_ns.namespace("hvxxx")
HVxxxComponent = hvxxx_ns.class_("HVxxxComponent", cg.PollingComponent, i2c.I2CDevice)
HVxxxCalibrateButton = hvxxx_ns.class_(
    "HVxxxCalibrateButton", button.Button, cg.Parented
)

CONF_ADDRESS = "address"
CONF_PRESSURE = "pressure"
CONF_TEMPERATURE = "temperature"
CONF_OFFSET_NUMBER = "offset_value"

CONF_CHIP_MODEL = "model"

CONF_PRESSURE_RANGE = "pressure_range"
CONF_IO_WATCHDOG = "io_watchdog"
CONF_BANDWIDTH = "bandwidth_limit"
CONF_NOTCH = "notch"
CONF_FRIENDLY_NAME = "friendly_name"

CONF_RATE_CONTROL = "rate_control"
CONF_TEMPLATE_NO = "template"
# There is no settings for refresh rate; it is derived from update interval which is set in the polling component schema.
# REFRESH_RATE_MODES = { 111hz, 55.5hz, 37hz... etc }


def validate_range(config):
    model = config[CONF_CHIP_MODEL]
    rng = config[CONF_PRESSURE_RANGE]
    if rng not in PRESSURE_RANGE_TO_BITS[model]:
        raise cv.Invalid(f"pressure_range {rng} is not valid for model {model}")
    return config


CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(HVxxxComponent),
            cv.Required(CONF_ADDRESS): cv.int_range(min=0x28, max=0x31),
            cv.Required(CONF_CHIP_MODEL): cv.one_of(*MODEL_OPTIONS, upper=True),
            cv.Required(CONF_PRESSURE_RANGE): cv.one_of(
                *PRESSURE_RANGE_OPTIONS, lower=True
            ),
            cv.Required(CONF_BANDWIDTH): cv.one_of(*BANDWIDTH_MODES, lower=True),
            cv.Optional(CONF_NOTCH, default=True): cv.boolean,
            cv.Optional(CONF_IO_WATCHDOG, default=False): cv.boolean,
            cv.Optional(CONF_RATE_CONTROL, default=0): cv.int_range(min=0, max=255),
            # Optional top-level naming helpers (not strictly required for operation)
            cv.Optional(CONF_NAME): cv.string,
            cv.Optional(CONF_FRIENDLY_NAME): cv.string,
            cv.Optional(CONF_TEMPERATURE): sensor.sensor_schema(
                unit_of_measurement=UNIT_CELSIUS,
                icon=ICON_THERMOMETER,
                accuracy_decimals=1,
                device_class=DEVICE_CLASS_TEMPERATURE,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
        }
    )
    # update_interval is used to derive the Rate Control register (refresh rate)
    .extend(cv.polling_component_schema("0.5s"))
    # I²C address – 0x28 is typical, but can be overridden in YAML
    .extend(i2c.i2c_device_schema(None))
    # Custom validation to ensure pressure range is valid for selected model
    .add_extra(validate_range)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await i2c.register_i2c_device(var, config)

    # if CONF_PRESSURE in config:
    #     pressure_sensor = await sensor.new_sensor(config[CONF_PRESSURE])
    #     cg.add(var.set_pressure_sensor(pressure_sensor))
    # else:
    pressure_sensor_schema = sensor.sensor_schema(
        unit_of_measurement=UNIT_PASCAL,
        icon=ICON_GAUGE,
        accuracy_decimals=2,
        device_class=DEVICE_CLASS_PRESSURE,
        state_class=STATE_CLASS_MEASUREMENT,
    )
    pressure_sensor_conf = pressure_sensor_schema(
        {
            cv.CONF_ID: f"{config[CONF_ID]}_pressure",
            cv.CONF_NAME: f"{config.get(CONF_NAME, 'HVxxx')} Pressure",
        }
    )
    pressure_sensor = await sensor.new_sensor(pressure_sensor_conf)
    cg.add(var.set_pressure_sensor(pressure_sensor))

    # Temperature sensor: only create if user set include_temperature: true
    # AND provided a temperature: block (so we have a name, etc.)
    if CONF_TEMPERATURE in config:
        temperature_sensor = await sensor.new_sensor(config[CONF_TEMPERATURE])
        cg.add(var.set_temperature_sensor(temperature_sensor))

    # Create offset number sensor based on defaults from  cv.Optional(CONF_OFFSET_NUMBER): sensor.sensor_schema(
    # even if user did not provide an offset_number: block

    offset_number_schema = sensor.sensor_schema(
        unit_of_measurement=UNIT_PASCAL,
        icon=ICON_GAUGE,
        accuracy_decimals=2,
        device_class=DEVICE_CLASS_PRESSURE,
        state_class=STATE_CLASS_MEASUREMENT,
    )
    offset_number_conf = offset_number_schema(
        {
            cv.CONF_ID: f"{config[CONF_ID]}_offset_number",
            cv.CONF_NAME: f"{config.get(CONF_NAME, 'HVxxx')} Offset",
        }
    )
    offset_number_sensor = await sensor.new_sensor(offset_number_conf)
    cg.add(var.set_offset_number_sensor(offset_number_sensor))

    # Pressure range bits and full-scale value (in inH2O) based on model specifications
    model_key = config[CONF_CHIP_MODEL]
    range_key = config[CONF_PRESSURE_RANGE]
    range_bits = PRESSURE_RANGE_TO_BITS[model_key][range_key]
    pressure_range_inh2o = float(range_key.replace("inh2o", ""))

    cg.add(var.set_user_model_name(model_key))
    cg.add(var.set_pressure_range(pressure_range_inh2o))
    cg.add(var.set_pressure_range_bits(range_bits))
    cg.add(var.set_io_watchdog_enabled(config.get(CONF_IO_WATCHDOG, False)))
    cg.add(var.set_rate_control_value(config.get(CONF_RATE_CONTROL, 0)))

    bandwidth_text_value = config[CONF_BANDWIDTH]  # e.g. "10hz" or "auto"
    bandwidth_value_hz = (
        0.0
        if bandwidth_text_value == "auto"
        else float(bandwidth_text_value.replace("hz", ""))
    )
    cg.add(var.set_bandwidth_limit_hz(bandwidth_value_hz))
    cg.add(var.set_bandwidth_mode_bits(BANDWIDTH_MODES[bandwidth_text_value]))
    cg.add(var.set_notch_filter_enabled(config.get(CONF_NOTCH, True)))

    # Get the base name from the component's name or the pressure sensor's name.
    base_name = config[CONF_NAME]
    # Get the main component's ID to create unique IDs for sub-entities.
    base_id = str(config[CONF_ID])

    # Add a button to trigger zero-offset calibration
    calibration_btn_schema = button.button_schema(
        HVxxxCalibrateButton,
        device_class=button.DEVICE_CLASS_RESTART,
        entity_category=ENTITY_CATEGORY_CONFIG,
    )
    calibration_btn_conf = calibration_btn_schema(
        {
            cv.CONF_ID: f"{base_id}_calibrate_button",
            "name": f"Calibrate {base_name}",
        }
    )
    calibration_btn = await button.new_button(calibration_btn_conf)
    await cg.register_parented(calibration_btn, config[CONF_ID])
    cg.add(var.set_calibrate_button(calibration_btn))

    # Create zero-offset calibration number for long-term storage

    # Text sensor reporting model retrieved from the device NOT defined in YAML
    model_ts_conf = text_sensor.text_sensor_schema()(
        {cv.CONF_ID: f"{base_id}_model", "name": f"{base_name} Model"}
    )
    model_ts = await text_sensor.new_text_sensor(model_ts_conf)
    cg.add(var.set_model_text_sensor(model_ts))

    # Text sensor reporting serial number retrieved from the device NOT defined in YAML
    serial_ts_conf = text_sensor.text_sensor_schema()(
        {cv.CONF_ID: f"{base_id}_serial", "name": f"{base_name} Serial"}
    )
    serial_ts = await text_sensor.new_text_sensor(serial_ts_conf)
    cg.add(var.set_serial_text_sensor(serial_ts))
