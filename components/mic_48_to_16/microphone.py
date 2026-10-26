import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import audio, microphone
from esphome.const import CONF_ID

DEPENDENCIES = ["esp32"]
ns = cg.esphome_ns.namespace("mic_48_to_16")
Microphone48To16 = ns.class_("Microphone48To16", microphone.Microphone, cg.Component)

def stream_limits(config):
    audio.set_stream_limits(min_bits_per_sample=16, max_bits_per_sample=16,
                            min_channels=1, max_channels=1,
                            min_sample_rate=16000, max_sample_rate=16000)(config)
    return config

CONFIG_SCHEMA = cv.All(microphone.MICROPHONE_SCHEMA.extend({
    cv.GenerateID(): cv.declare_id(Microphone48To16),
    cv.Required("source_microphone"): cv.use_id(microphone.Microphone),
    cv.Optional("sample_rate", default=16000): cv.one_of(16000, int=True),
    cv.Optional("bits_per_sample", default=16): cv.one_of(16, int=True),
    cv.Optional("num_channels", default=1): cv.one_of(1, int=True),
}).extend(cv.COMPONENT_SCHEMA), stream_limits)

FINAL_VALIDATE_SCHEMA = audio.final_validate_audio_schema(
    "mic_48_to_16", audio_device="source_microphone", sample_rate=48000,
    channels=1, bits_per_sample=16, audio_device_issue=True)

async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await microphone.register_microphone(var, config)
    cg.add(var.set_source(await cg.get_variable(config["source_microphone"])))
