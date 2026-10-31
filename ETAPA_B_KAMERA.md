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


# Stage B – USB Camera

Jelly Comb (1BCF:28C4, Windows: FHD Camera) works.
Nulaxy (0C45:636B, Windows: USB 2.0 Camera) works.
Logitech C270 (046D:0825) is not recognized during testing on the P4: the USB host reports 0 devices.

## Configuration

`esp32p4-camera.yaml` incorporates `esp32p4.yaml` via `packages`. The original file remains unchanged. HuskyLens, I2C, Ethernet, `media_player`, speaker, codec, and amplifier control are inherited without modification. Existing `!secret` references are also preserved.

Added:
- ESP-IDF explicitly set to 5.5.5; ESPHome version 2026.9.0 used for verification.
- PSRAM mode: `hex`, speed: 200 MHz.
- Dedicated build directory: `.esphome/build/esp32p4-camera`.
- External `esp_video_camera` component from `youkorr/esphome` (commit `53a315e76c69178d913e6744314408a98bc87234`).
- UVC, 640x480 resolution, `max_framerate` 10, `usb_peripheral_map` 0x01.
- No `usb_host`, BLE proxy, or HomeKey.
- Local `camera_log_compat`: defines the `ESPHOME_LOG_TAG` macro—used by a more recent PR—as a standard `static const char *const`. Intended for the verified ESPHome version 2026.9.0. Re-evaluate the need for this compatibility when updating ESPHome.
  The source for the pinned component remains unchanged.

MJPEG is not a standalone YAML option: the UVC branch requests V4L2 JPEG and passes the compressed
frames directly. `max_framerate` limits the stream passed to HA; it does not configure the USB
camera's frame rate. `jpeg_quality` is a parameter belonging to a different branch that performs hardware encoding.



The pinned component requires `esp_video` 2.3.0 and `usb_host_uvc` 2.5.*; it does not automatically
upgrade to an unreleased fix. The actual resolved dependencies and build status
are listed below.

## Actual Resolved Dependencies

Source: a copy of `investigation/camera/dependencies.lock` from this build.

| Component | Resolved Version |
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
| esphome/noise-c | lock specifies `*`; checkout `0266a6f871dfb278956be2c1f9a1b11d179c701f` |
| esphome/libsodium | lock specifies `*`; checkout `0266a6f871dfb278956be2c1f9a1b11d179c701f` |


