# Etapa D1 — test vestavěného mikrofonu

Konfigurace: `esp32p4-microphone-test.yaml`. Datum: 21. 10. 2026.
Jde o ověření vstupu zvuku; živý poslech, ukládání vzkazů a hlasový asistent
nejsou součástí tohoto kroku.

## Změny

- Nová varianta dědí `esp32p4-camera-720p.yaml`, včetně kamery, HuskyLens
  a media_player. Původní tři YAML soubory se neupravují.
- Samostatný sestavovací adresář `.esphome/build/esp32p4-microphone-test`.
- Mikrofon přes ES8311: GPIO11, společná I²S sběrnice, 48 kHz, 16 bit,
  levý kanál, MCLK ×256, bez PDM, s korekcí stejnosměrné složky.
- V této variantě je mikrofonní zisk ES8311 nastaven na 24 dB místo
  výchozích 42 dB. Parametry přehrávání se nemění. Správný kanál a zisk
  je ještě potřeba ověřit na desce.
- Dvě tlačítka v HA: **Mikrofon test 30 s** a **Mikrofon stop**.
- Diagnostika **Mikrofon snima**, **Mikrofon RMS**, **Mikrofon Peak**.
- Po startu zařízení zůstává snímání vypnuté. Test běží 30 sekund po
  úspěšném startu mikrofonu, lze jej předčasně zastavit. Opakované stisknutí
  během běžícího testu nespouští další paralelní snímání.
- Test se odmítne spustit při aktivním reproduktoru nebo selhání kodeku.
  Na rozběhnutí mikrofonu čeká nejvýše 5 sekund, pak požádá o zastavení.

Stage D1 — Built-in Microphone Test
Configuration: `esp32p4-microphone-test.yaml`. Date: October 21, 2026. This stage focuses on verifying audio input; live monitoring, message recording, and voice assistant functionality are not included.

Changes
This new variant inherits from `esp32p4-camera-720p.yaml`, including the camera, HuskyLens, and `media_player`. The original three YAML files remain unmodified.
A separate build directory is used: `.esphome/build/esp32p4-microphone-test`.
Microphone via ES8311: GPIO11, shared I²S bus, 48 ​​kHz, 16-bit, left channel, MCLK ×256, no PDM, with DC offset correction.
In this variant, the ES8311 microphone gain is set to 24 dB (down from the default 42 dB). Playback parameters remain unchanged. The correct channel and gain settings still require physical verification on the board.
Two buttons in HA: "Microphone Test 30s" and "Microphone Stop."
Diagnostics: "Microphone Capturing," "Microphone RMS," and "Microphone Peak."
Capture remains disabled upon device startup. The test runs for 30 seconds once the microphone has successfully initialized; it can also be stopped manually before the time elapses. Pressing the button again while a test is already in progress will not trigger a concurrent capture session.
The test will not start if the speaker is active or if the codec fails to initialize. The system waits up to 5 seconds for the microphone to start; if it fails to do so, it triggers a stop command.

