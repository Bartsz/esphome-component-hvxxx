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

DEPENDENCIES = ["i2c"]

hvxxx_ns = cg.esphome_ns.namespace("hvxxx")
HVxxxComponent = hvxxx_ns.class_("HVxxxComponent", cg.PollingComponent, i2c.I2CDevice)

# Template number class for storing calibration offset
template_ns = cg.esphome_ns.namespace("template_")
TemplateNumber = template_ns.class_(
    "TemplateNumber", number.Number, cg.PollingComponent
)

# Button to trigger calibration
HVxxxCalibrateButton = hvxxx_ns.class_("HVxxxCalibrateButton", button.Button)

CONF_ADDRESS = "address"
CONF_PRESSURE = "pressure"
CONF_TEMPERATURE = "temperature"
CONF_CHIP_MODEL = "model"

CONF_PRESSURE_RANGE = "pressure_range"
CONF_IO_WATCHDOG = "io_watchdog"
CONF_BANDWIDTH = "bandwidth_limit"
CONF_NOTCH = "notch"
CONF_FRIENDLY_NAME = "friendly_name"

CONF_RATE_CONTROL = "rate_control"

MODEL_OPTIONS = [
    "HV160",
    "HV120",
    "HV110",
    "HV210",
]

# Allowed pressure ranges, taken from datasheet, in inH2O.
PRESSURE_RANGE_OPTIONS = [
    "0.1inh2o",
    "0.25inh2o",
    "0.5inh2o",
    "1inh2o",
    "2.5inh2o",
    "5inh2o",
    "10inh2o",
    "20inh2o",
    "30inh2o",
    "40inh2o",
    "50inh2o",
    "60inh2o",
]

PRESSURE_RANGE_TO_BITS = {
    "HV160": {
        "2.5inh2o": 0,
        "5inh2o": 1,
        "10inh2o": 2,
        "20inh2o": 3,
        "30inh2o": 4,
        "40inh2o": 5,
        "50inh2o": 6,
        "60inh2o": 7,
    },
    "HV120": {
        "2.5inh2o": 4,
        "5inh2o": 5,
        "10inh2o": 6,
        "20inh2o": 7,
    },
    "HV110": {
        "0.5inh2o": 2,
        "1inh2o": 3,
        "2.5inh2o": 4,
        "5inh2o": 5,
        "10inh2o": 6,
    },
    "HV210": {
        "0.1inh2o": 0,
        "0.25inh2o": 1,
        "0.5inh2o": 2,
        "1inh2o": 3,
        "2.5inh2o": 4,
        "5inh2o": 5,
        "10inh2o": 6,
    },
}

# Bits 4–7 of the Mode register
BANDWIDTH_MODES = {
    "0.1hz": 0,
    "0.25hz": 1,
    "0.5hz": 2,
    "1hz": 3,
    "2.5hz": 4,
    "5hz": 5,
    "10hz": 6,
    "auto": 7,
}

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
            cv.Required(CONF_PRESSURE): sensor.sensor_schema(
                unit_of_measurement=UNIT_PASCAL,
                icon=ICON_GAUGE,
                accuracy_decimals=2,
                device_class=DEVICE_CLASS_PRESSURE,
                state_class=STATE_CLASS_MEASUREMENT,
            ),
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

    pressure = await sensor.new_sensor(config[CONF_PRESSURE])
    cg.add(var.set_pressure_sensor(pressure))

    # Prefer explicit component name if provided, else pressure sensor name
    base_name = config.get(CONF_NAME, config[CONF_PRESSURE]["name"])  # noqa: F821
    # Temperature sensor: only create if user set include_temperature: true
    # AND provided a temperature: block (so we have a name, etc.)
    if CONF_TEMPERATURE in config:
        temperature = await sensor.new_sensor(config[CONF_TEMPERATURE])
        cg.add(var.set_temperature_sensor(temperature))

    model_name = base_name + " Model"
    model_ts_schema = text_sensor.text_sensor_schema()
    model_ts_conf = model_ts_schema({"name": model_name})
    model_ts = await text_sensor.new_text_sensor(model_ts_conf)
    cg.add(var.set_model_text_sensor(model_ts))

    serial_name = base_name + " Serial"
    serial_ts_schema = text_sensor.text_sensor_schema()
    serial_ts_conf = serial_ts_schema({"name": serial_name})
    serial_ts = await text_sensor.new_text_sensor(serial_ts_conf)
    cg.add(var.set_serial_text_sensor(serial_ts))

    # Pressure range bits and full-scale value (in inH2O)
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

    # Create calibration offset number for long-term storage
    offset_number_name = base_name + " Calibration Offset"
    offset_schema = number.number_schema(
        TemplateNumber,
        entity_category=ENTITY_CATEGORY_CONFIG,
    )

    # Minimal config: just name; set behavior via C++ setters below
    offset_conf = offset_schema(
        {
            "name": offset_number_name,
        }
    )

    # min/max/step define allowed range and UI slider granularity
    offset_number = await number.new_number(
        offset_conf,
        min_value=-2.5,
        max_value=2.5,
        step=0.01,
    )

    await cg.register_parented(offset_number, config[CONF_ID])
    # Configure behavior on the C++ object directly
    cg.add(offset_number.set_optimistic(True))
    cg.add(offset_number.set_initial_value(0.0))
    cg.add(offset_number.set_restore_value(True))
    cg.add(var.set_offset_number(offset_number))

    # Add a button to trigger zero-offset calibration
    calibration_btn_schema = button.button_schema(
        HVxxxCalibrateButton,
        entity_category=ENTITY_CATEGORY_CONFIG,
    )

    calibration_btn_conf = calibration_btn_schema({"name": f"Calibrate {base_name}"})

    calibration_btn = await button.new_button(calibration_btn_conf)
    await cg.register_parented(calibration_btn, config[CONF_ID])

    # wire the button to the component
    cg.add(calibration_btn.set_parent(var))
    cg.add(var.set_calibrate_button(calibration_btn))
