"""D4 recorder: reuse the pinned Audio Stack microphone and upload to Voice Inbox."""
import re
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import esp32, text_sensor, voip_stack
from esphome.components.esp_audio_stack.microphone import ESPAudioStackMicrophone
from esphome.const import CONF_ID

DEPENDENCIES = ["esp32", "esp_audio_stack", "voip_stack", "psram"]
AUTO_LOAD = ["text_sensor"]
ns = cg.esphome_ns.namespace("p4_voice_inbox")
P4VoiceInbox = ns.class_("P4VoiceInbox", cg.Component)


def source_name(value):
    value = cv.string_strict(value)
    if not re.fullmatch(r"[a-z][a-z0-9_-]{0,31}", value):
        raise cv.Invalid("Use the exact Voice Inbox source identifier (a-z, 0-9, _ or -)")
    return value


def source_key(value):
    value = cv.string_strict(value)
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise cv.Invalid("Use the source's 64-character lowercase hexadecimal upload key")
    return value


CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(P4VoiceInbox),
    cv.Required("microphone_id"): cv.use_id(ESPAudioStackMicrophone),
    cv.Required("phone_id"): cv.use_id(voip_stack.VoipStack),
    cv.Required("receiver_ip"): cv.ipv4address,
    cv.Optional("receiver_port", default=8123): cv.port,
    cv.Required("source"): source_name,
    cv.Required("key"): source_key,
    cv.Required("status"): text_sensor.text_sensor_schema(),
}).extend(cv.COMPONENT_SCHEMA)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    cg.add(var.set_microphone(await cg.get_variable(config["microphone_id"])))
    cg.add(var.set_phone(await cg.get_variable(config["phone_id"])))
    cg.add(var.set_receiver(str(config["receiver_ip"]), config["receiver_port"], config["source"], config["key"]))
    cg.add(var.set_status_sensor(await text_sensor.new_text_sensor(config["status"])))
    esp32.include_builtin_idf_component("esp_http_client")
