# Etapa B – USB kamera

Upřesnění 21. 10. 2026: celé dosavadní testování včetně dodaných logů proběhlo
dle uživatele na Jelly Comb (1BCF:28C4, Windows: FHD Camera). Druhá kamera
Nulaxy (0C45:636B, Windows: USB 2.0 Camera) byla také samostatně otestována
a funguje. Uvedené statistiky patří Jelly Comb, nikoli Nulaxy nebo Logitechu.
Původní přiřazení úspěšných testů Logitechu C270 bylo chybné.
C270 (046D:0825) při testu na P4 není rozpoznána: USB host hlásí 0 zařízení.

Datum: 20. 10. 2026. Bez flashování.

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

## Oprava USB #538 / #571

PR https://github.com/espressif/esp-usb/pull/571 byl sloučen 6. 10. 2026.
Oprava znovu vybere alternativní isochronní rozhraní podle vyjednaného payloadu.
Issue https://github.com/espressif/esp-usb/issues/538 je uzavřený s milníkem 2.6.1.
Milník však není důkaz vydání.

Při kontrole 20. 10. 2026 endpoint registru
https://components.espressif.com/components/espressif/usb_host_uvc/versions/2.6.1/changelog
vrátil HTTP 404. Aktuálně stažený upstream CHANGELOG končí 2.6.0 z 16. 9. 2026.
Vydanou verzi obsahující #571 se tedy nepodařilo doložit.
Zdroj: https://github.com/espressif/esp-usb/blob/master/host/class/uvc/usb_host_uvc/CHANGELOG.md

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
Logy: `investigation/camera/config.log` a `investigation/camera/build.log`.
Projekt neobsahoval secrets.yaml, proto byly pro sestavení vytvořeny dočasné
testovací údaje. Binárka s nimi není určena k nasazení. Produkční secrets musí
dodat uživatel před vlastním sestavením pro desku.
Dočasný secrets.yaml byl po dokončení odstraněn a testovací údaje byly
odstraněny z reportových logů. Velikosti a SHA-256 binárek jsou uložené v
`investigation/camera/build-artifacts.json`.

První plná kompilace selhala na `esp_video_camera.cpp:50`: ESPHome 2026.9.0
nezná `ESPHOME_LOG_TAG`. Následné chyby neznámého TAG jsou důsledkem stejné
příčiny, nikoli dalších problémů USB. První log:
`investigation/camera/build-first-failure.log`.
Po přidání camera_log_compat validace i plná kompilace prošly:
`INFO Successfully compiled program.` Výstupní kód 0.

Příkazy ověření:
```
.venv/Scripts/python.exe -m esphome config esp32p4-camera.yaml
.venv/Scripts/python.exe -m esphome compile esp32p4-camera.yaml
```
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

Soubory jsou v `.esphome/build/esp32p4-camera/build/`. Jsou pouze dokladem
sestavitelnosti s dočasnými testovacími údaji, nikoli firmwarem pro nasazení.
Spotřeba PSRAM za běhu, špičky alokací, FPS a souběh s audiem se bez měření na
desce určit nedají. Statická RAM z linkeru není celková spotřeba paměti za běhu.

## Následný test na desce – až po úspěšném sestavení

### Výsledek uživatelského testu 20. 10. 2026

Uživatel potvrdil funkční USB kameru s naší variantou esp32p4-camera.yaml.
Přiložený log z 22:39–22:42 dokládá běžící firmware ESPHome **2026.9.1**
(lokální kompilace výše byla 2026.9.0), ESP32-P4 rev1.3, PSRAM 32768 KB,
Ethernet 100 Mb/s full duplex a UVC /dev/video40 v rozlišení 640x480.
Po úvodním hlášení 12,2 fps následují 7,5 / 8,1 / 8,1 / 8,3 fps při
49 688–56 820 B/snímek. Úvodní údaj přesahuje nastavený limit 10 fps;
příčina není tímto výřezem doložena. Dlouhodobých 10 fps z logu potvrdit nelze.

Audio pipeline načetla FLAC 48 kHz / mono / 16 bit, přešla do PLAYING,
spustila I2S speaker a poté se vrátila do IDLE. To nepotvrzuje slyšitelný zvuk
ani souběh s obrazem: audio skončilo před uvedenými statistikami kamery.
I2C našlo 0x18 a 0x32; správnost detekcí HuskyLens výřez neukazuje.

Log obsahuje `Last reset too quick; invoke in 6 restarts`. Je to záznam
počítadla krátkých předchozích běhů, nikoli důkaz pádu kamery; příčina restartů
není doložená. Ve výřezu nejsou chyby USB, alokace ani watchdogu.
Zbývá delší souběžný test obrazu, audia a HuskyLens a měření volné PSRAM.
Následně uživatel výslovně potvrdil současný běh: kamera běží, hudba hraje
a HuskyLens načítá. Souběh všech tří funkcí a slyšitelný zvuk jsou tedy
ověřené uživatelským testem. Délka testu, volná PSRAM a příčina dřívějších
krátkých restartů nebyly uvedeny. Základ 640x480 je funkčně ověřený.
Etapa C dosud nebyla zahájena.

1. Zkontrolovat 5V VBUS při PoE s připojenou C270.
2. S vlastním secrets.yaml znovu sestavit. V této etapě se neflashuje.
3. Při pozdějším povoleném testu očekávat
   `USB Host installed (peripheral map 0x1)` a
   `Capture resolution: 640x480 (JPEG)`.
4. Otevřít kamerovou entitu přes ESPHome integraci HA. Při odběru obrazu
   očekávat statistiky rozlišení, fps a B/frame.
5. Ověřit současné audio a aktualizace HuskyLens; sledovat volnou interní
   paměť i PSRAM a největší volný blok. Zkusit odpojení a znovupřipojení kamery.
6. Při opakovaných `missed EoF`, chybách vyjednání, timeoutu, restartu watchdogem
   nebo poklesu napájení nepokračovat na 720p.
