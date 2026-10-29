# Etapa 2 – reproduktor a ES8311

Celý výsledný YAML je v `esp32p4.yaml`. K němu patří lokální složka `components`
z první etapy. Deska: Waveshare ESP32-P4-WIFI6-POE-ETH s ESP32-C6.

## Změny

| Signál | GPIO / nastavení |
|---|---|
| I2C SDA / SCL | GPIO7 / GPIO8, sdílená sběrnice `bus_a` |
| ES8311 | I2C adresa 0x18 |
| I2S MCLK | GPIO13 |
| I2S BCLK / SCLK | GPIO12 |
| I2S LRCLK / LRCK | GPIO10, opraveno z GPIO11 |
| Data z P4 do ES8311 DSDIN | GPIO9, opraveno z GPIO10 |
| Data z ES8311 do P4 | GPIO11, pro přehrávání se nepoužívá |
| NS4150B PA_CTRL | GPIO53, vysoká úroveň zapíná zesilovač |

Zapojení je ověřeno v oficiálním schématu, první list, bloky Codec U10 a
PA&SPEAKER&MIC U8. Polaritu PA_CTRL potvrzuje také audio příklad výrobce.
Audio GPIO9/10/12/13/53 nekolidují s Ethernetem (GPIO28–31, 34–35, 49–52),
SDIO k C6 (GPIO14–19) ani SD kartou (GPIO39–45). I2C záměrně sdílí HuskyLens
a kodek; adresy 0x32 a 0x18 se liší.

Doplněna existující komponenta `audio_dac: platform: es8311` a vazba
`speaker.audio_dac: es8311_dac`, aby přehrávač mohl řídit hlasitost a ztlumení kodeku.
Kodek, I2S reproduktor a preferovaný formát přehrávače používají 48 kHz,
kodek a reproduktor 16 bitů. Mono kodek přijímá levý I2S kanál. MCLK používá
násobek 256, tedy při 48 kHz frekvenci 12,288 MHz.

Zesilovač je po inicializaci GPIO vypnutý (`ALWAYS_OFF`). Zapíná se v `on_boot`
až po inicializaci komponent, pouze pokud kodek není označen jako nefunkční.
Při řádném vypnutí/restartu jej `on_shutdown` vypne. Mezi přehráváními zůstává
zapnutý; ztlumení řídí kodek. Nejde o záruku odstranění všech zapínacích lupnutí.

Počáteční hlasitost je 0.3; původní rozsah 0.3–0.8 je zachován.
Zůstává původní jediná `announcement_pipeline` s preferovaným FLAC / 48 kHz / mono.
Nepřidávám souběžnou hudební větev ani mixer. Mikrofon a voice_assistant nejsou
nakonfigurované. HuskyLens, API a tajemství z první etapy zůstávají zachované.


## Zdroje

- [Oficiální schéma – první list](https://files.waveshare.com/wiki/ESP32-P4-WIFI6-POE-ETH/ESP32-P4-WIFI6-POE-ETH-Schematic.pdf)
- [Waveshare – I2S Audio Demo](https://www.waveshare.com/wiki/ESP32-P4-WIFI6-POE-ETH)
- [ESPHome ES8311](https://esphome.io/components/audio_dac/es8311/)
- [ESPHome I2S speaker](https://esphome.io/components/speaker/i2s_audio/)
- Schéma a generátor instalovaného ESPHome 2026.9.0: komponenty `es8311`,
  `speaker` a `i2s_audio`.


