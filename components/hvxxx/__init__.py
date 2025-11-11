"""HVxxx pressure sensor external component for ESPHome.

This module exposes the top-level YAML integration block `hvxxx:`.
ESPHome looks for CONFIG_SCHEMA and to_code at the package root, so we
re-export them from the implementation module.
"""

from .sensor import (  # re-export for ESPHome loader
	CONFIG_SCHEMA,  # noqa: F401
	to_code,  # noqa: F401
)

# Optional: hint ESPHome about components this integration uses so they are
# available even if not referenced elsewhere.
AUTO_LOAD = [
	"i2c",
	"sensor",
	"text_sensor",
	"number",
	"button",
	"template",  # ensure template number component headers available even if created programmatically
]

__version__ = "0.1.0"
