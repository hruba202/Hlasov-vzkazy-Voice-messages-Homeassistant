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



