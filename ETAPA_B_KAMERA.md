# Etapa B – USB kamera

 Jelly Comb (1BCF:28C4, Windows: FHD Camera)  funguje.
Nulaxy (0C45:636B, Windows: USB 2.0 Camera)  funguje. 
Logitech C270 (046D:0825) při testu na P4 není rozpoznána: USB host hlásí 0 zařízení.


## Konfigurace

`esp32p4-camera.yaml` přebírá `esp32p4.yaml` přes packages. Původní soubor se
nemění. HuskyLens, I2C, Ethernet, media_player, speaker, kodek a řízení zesilovače
se dědí beze změny. Zůstávají také původní odkazy !secret.

Přidáno:
- ESP-IDF explicitně 5.5.5, ESPHome pro ověření 2026.9.0.
- PSRAM mode hex, speed 200MHz.
- Samostatný build adresář `.esphome/build/esp32p4-camera`.
- Externí esp_video_camera z youkorr/esphome na
  `53a315e76c69178d913e6744314408a98bc87234`.
- UVC, 640x480, max_framerate 10, usb_peripheral_map 0x01.
- Žádný usb_host, BLE proxy ani HomeKey.
- Lokální `camera_log_compat`: definuje makro ESPHOME_LOG_TAG používané novějším
  PR jako běžné `static const char *const`. Určeno pro ověřovanou verzi ESPHome
  2026.9.0; při aktualizaci ESPHome znovu zkontrolovat potřebu této kompatibility.
  Zdroj připnuté komponenty zůstává nezměněný.

MJPEG není samostatná YAML volba: UVC větev žádá V4L2 JPEG a předává komprimované
snímky přímo. max_framerate omezuje předávání do HA; nenastavuje frekvenci USB
kamery. jpeg_quality je parametr jiné, hardwarově kódující větve.



Připnutá komponenta požaduje esp_video 2.3.0 a usb_host_uvc 2.5.*; automatický
přechod na nevydanou opravu se neprovádí. Skutečně vyřešené závislosti a stav
sestavení jsou uvedeny níže.

## Skutečně vyřešené závislosti

Zdroj: kopie `investigation/camera/dependencies.lock` z tohoto sestavení.

| Komponenta | Vyřešená verze |
|---|---|
| idf | 5.5.5 |
| espressif/esp_video | 2.3.0 |
| espressif/usb_host_uvc | 2.5.2 |
| espressif/esp_cam_sensor | 2.3.0 |
| espressif/esp_ipa | 2.2.0~1 |
| espressif/esp_h264 | 1.3.0 |
| espressif/esp_sccb_intf | 0.0.9 |
| espressif/cmake_utilities | 0.5.3 |
| espressif/mdns | 1.12.0 |
| esphome/esp-audio-libs | 3.2.1 |
| esphome/micro-flac | 0.2.0 |
| esphome/noise-c | lock uvádí `*`; checkout `0266a6f871dfb278956be2c1f9a1b11d179c701f` |
| esphome/libsodium | lock uvádí `*`; checkout `0266a6f871dfb278956be2c1f9a1b11d179c701f` |

Lock obsahuje rovněž kontrolní hashe balíčků. Jde o záznam tohoto sestavení,
nikoliv záruku, že budoucí čisté sestavení znovu vybere všechny stejné verze.
Checkout externí komponenty byl ověřen pomocí git rev-parse HEAD.
Stažený ovladač 2.5.2 neobsahuje funkci `uvc_select_alt_setting` z opravy #571.

## Ověření a omezení

`esphome config esp32p4-camera.yaml` prošlo. C++ byl vygenerován.
Porovnání po sloučení packages potvrdilo totožnost bloků huskylens_bridge,
sensor, binary_sensor, media_player, speaker, i2s_audio, audio_dac, switch,
i2c a ethernet vůči původnímu souboru. Výsledek je uložen v
`investigation/camera/preservation-check.txt`.

Při sestavení byla nastavena proměnná prostředí
`ESPHOME_IDF_DEFAULT_TARGETS=esp32p4` pro výběr nástrojů pouze pro tento čip.

| Výsledek | Velikost / využití |
|---|---|
| firmware.ota.bin (a esp32p4.bin) | 1 193 632 B |
| firmware.factory.bin | 1 259 168 B |
| Obraz podle linkeru, bez paddingu | 1 193 224 B |
| Aplikační oddíl | 16 515 072 B; využito přibližně 7,2 % |
| Interní DIRAM, staticky | 105 666 B / 576 464 B = 18,33 % |
| HP core RAM | 142 B |
| LP RAM | 56 B |
| External RAM, statické sekce | 1 112 668 B |

External RAM obsahuje .text 817 376 B, .rodata 294 760 B, .init_array 276 B
a .appdesc 256 B. Základ má zapnuté XIP z PSRAM. Výpis nástroje size používá
pro External RAM adresní oblast přibližně 128 MiB, proto jeho 0,83 % **není**
procento fyzické 32MiB PSRAM této desky. Statické sekce odpovídají přibližně
3,32 % z nominálních 32 MiB, bez dynamických alokací a rezervací.



