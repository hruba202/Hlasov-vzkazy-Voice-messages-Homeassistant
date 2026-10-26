"""Logging compatibility for esp_video_camera's pinned PR on ESPHome 2026.9.0."""

import esphome.codegen as cg
import esphome.config_validation as cv

CONFIG_SCHEMA = cv.Schema({})


async def to_code(config):
    # Same TAG declaration used by ESPHome 2026.9.0's own camera component.
    # Keep the upstream camera checkout unmodified.
    cg.add_define(
        "ESPHOME_LOG_TAG(tag, value)",
        cg.RawExpression("static const char *const tag = value"),
    )
