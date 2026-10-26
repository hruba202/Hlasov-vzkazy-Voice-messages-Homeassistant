import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import esp32, microphone, text_sensor
from esphome.const import CONF_ID

DEPENDENCIES = ["esp32", "microphone", "psram"]
AUTO_LOAD = ["text_sensor"]
ns = cg.esphome_ns.namespace("voice_recorder")
VoiceRecorder = ns.class_("VoiceRecorder", cg.Component)

def token(value):
    value = cv.string_strict(value)
    if len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise cv.Invalid("Use a random 64-character lowercase hexadecimal receiver token")
    return value

CONFIG_SCHEMA = cv.Schema({
    cv.GenerateID(): cv.declare_id(VoiceRecorder),
    cv.Required("microphone_id"): cv.use_id(microphone.Microphone),
    cv.Required("receiver_ip"): cv.ipv4address,
    cv.Optional("receiver_port", default=8099): cv.port,
    cv.Required("token"): token,
    cv.Required("status"): text_sensor.text_sensor_schema(),
}).extend(cv.COMPONENT_SCHEMA)

async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    cg.add(var.set_microphone(await cg.get_variable(config["microphone_id"])))
    cg.add(var.set_receiver(str(config["receiver_ip"]), config["receiver_port"], config["token"]))
    cg.add(var.set_status_sensor(await text_sensor.new_text_sensor(config["status"])))
    esp32.include_builtin_idf_component("esp_http_client")
