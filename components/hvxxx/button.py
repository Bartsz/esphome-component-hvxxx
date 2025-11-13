import esphome.codegen as cg
from esphome.components import button
import esphome.config_validation as cv
from esphome.const import ENTITY_CATEGORY_CONFIG, ICON_ROTATE_RIGHT
from .sensor import hvxxx_ns, HVxxxComponent


CalibrationButton = hvxxx_ns.class_(
    "HVxxxCalibrateButton", button.Button, cg.Parented.template(HVxxxComponent)
)

# Reference to the HVxxx component?
# Does this reference a parameter named "id" on hvxxx component or it is itself a value of an id?
# How do I create a YAML config that has multiple hvxxx components each with its own calibration button?

CONF_HVXXX_ID = "hvxxx_sensor_id"

CONFIG_SCHEMA = button.button_schema(
    CalibrationButton,
    entity_category=ENTITY_CATEGORY_CONFIG,
    icon=ICON_ROTATE_RIGHT,
).extend(
    {
        cv.GenerateID(CONF_HVXXX_ID): cv.use_id(HVxxxComponent),
    }
)


async def to_code(config):
    var = await button.new_button(config)
    # await cg.register_component(var, config)
    await cg.register_parented(var, config[CONF_HVXXX_ID])
