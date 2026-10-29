# Etapa 3 – HomeKey: návrh konfigurace a zjištěná překážka

**Etapa není dokončena jako funkční firmware.** Celý návrh je v
`esp32p4-homekey.yaml`; obsahuje také HuskyLens a audio z předchozích etap.
`esp32p4.yaml` zůstává konfigurací po etapě 2. Návrh HomeKey zatím nenahrávat.

YAML prošel validací i generováním C++ v ESPHome 2026.9.0 / ESP-IDF 5.5.5.
Kontrola zdrojového kódu ovšem odhalila konkrétní překážku kompilace pro P4
v závislosti HAP-ESPHome a nevyřešenou volbu Ethernet transportu.
Úspěšná validace tedy není potvrzením kompatibility.

## Překážky v požadovaném upstreamu

Kontrolováno 20. 10. 2026:

- HAP-ESPHome `main`: `0ab12c97f33d894909a35b24b9e837384d063861`.
- esp-homekit-sdk `esphome`: `1d1ea30bba62ed9c9d55da6613d828a658ec2a39`.
- HomeKey knihovnu volí HAP-ESPHome jako HK-HomeKit-Lib
  `c6a5b958bf4312c53df2c9e6aebe846336998861`.

1. `esp_hap_platform/CMakeLists.txt` zařazuje `src/esp_mfi_i2c.c` pro všechny čipy
   kromě ESP8266. Soubor má výběr ROM hlavičky pro ESP32/S2/S3/C3/C2/C6, ale
   chybí P4. Pro P4 proto vybere větev `#error "please include ets_sys.h"`.
   Tuto překážku jsem zjistil kontrolou zdrojů; úplnou kompilaci jsem nespouštěl.
2. `HAPRootComponent.cpp` volá `hap_init(HAP_TRANSPORT_WIFI)` a přidává Wi-Fi
   transport service, přestože projekt používá Ethernet. SDK zná
   `HAP_TRANSPORT_ETHERNET` a v `hap_is_network_configured()` jej rozlišuje.
   YAML upstreamu nenabízí přepínač transportu.
3. SDK navíc obsahuje přímá volání `esp_wifi_*`, závislost na `esp_wifi` a získávání
   MAC přes `esp_wifi_get_mac()`. P4 nemá vlastní rádio. Pouhá změna transportní
   konstanty proto není dostatečný důkaz funkce celé sestavy.

K dokončení na P4 je potřeba port/oprava těchto závislostí, následná úplná kompilace
a zkouška párování po Ethernetu a autentizace telefonu.

Oprava mého předběžného závěru z etapy 1: obecná závislost Python komponenty
na `network` sama o sobě nepotvrzuje Ethernet podporu její implementace.

## Co je v návrhu hotové

- Požadovaný zdroj externích komponent a výslovný výběr `homekit_base`, `homekit`,
  `pn532`, `pn532_spi`. Použijí se upravené NFC komponenty z HAP-ESPHome.
- ESP-IDF 5.5.5, stejně jako při ověřování etapy 2, a všechny tři požadované
  `sdkconfig_options` uvnitř `esp32.framework`.
- SPI sběrnice a PN532 s intervalem 100 ms.
- Template lock `this_lock`, `optimistic: true`, logování zamknutí/odemknutí,
  vazba `nfc_id` a provedení stejného přepnutí stavu po úspěšném HomeKey jako
  v předloze. Neúspěšná autentizace pouze zapisuje log. Povrch `SILVER` zachován.
- Zpřesněný jmenný prostor konstanty `lock::LOCK_STATE_LOCKED`; přejmenovány
  pouze logovací tagy, rozhodovací logika zůstává stejná.
- HomeKit párovací kód je `!secret homekit_setup_code`, API a OTA také přes secrets.
- Výslovně povolené mDNS. Síť nadále zajišťuje Ethernet.

Zámek je stejně jako v předloze **pouze stavová entita**. Neovládá fyzické relé
ani motor a nepotvrzuje skutečnou polohu dveří. Logika při úspěšné autentizaci
střídá zamknuto/odemknuto;

## Návrh zapojení PN532 na 40pin header P6

| PN532 signál | GPIO ESP32-P4 |
|---|---|
| SCK | GPIO2 |
| MISO | GPIO3 |
| MOSI | GPIO4 |
| SS / CS | GPIO5 |
| GND | GND desky |

GPIO2–5 jsou ve schématu vyvedeny na P6. Nejsou to fyzická čísla kontaktů
konektoru! Před zapojením vyhledejte jejich označení na pinoutu konkrétní revize.
Přiřazení čísla fyzického kontaktu zde neodhaduji.

Navržené GPIO nekolidují s Ethernetem (28–31, 34–35, 49–52), SDIO k C6 (14–19,
reset 54), SD kartou (39–45), audiem (9–13, 53) ani I2C (7–8).
Nepřebírají SPI piny 10–13 z předlohy pro S3, které jsou na této desce obsazené audiem.

Na PN532 nastavit přepínače/jumpery do SPI podle konkrétního modulu. Signály musí
mít 3,3V logické úrovně; napájecí vstup ověřit podle typu breakout modulu
(samotný údaj „PN532“ neurčuje jeho regulátor ani převodníky úrovní).
IRQ a reset nejsou v této konfiguraci použity.

## Partition table a úložiště

Kontrolovaný SDK používá standardní oddíl `nvs` pro provozní data. Nepřítomnost
`factory_nvs` při inicializaci výslovně toleruje; není důvod jej pro tento návrh
automaticky přidávat. HomeKey data se ukládají do NVS namespace `HK_DATA`.

ESPHome pro tento návrh a `flash_size: 32MB` vygeneroval:

| Oddíl | Typ | Velikost |
|---|---|---|
| otadata | data/ota | 0x2000 |
| phy_init | data/phy | 0x1000 |
| app0 | app/ota_0 | 0xFC0000 |
| app1 | app/ota_1 | 0xFC0000 |
| nvs | data/nvs | 0x70000 |

Vlastní partition table tedy nepřidávám. Po úspěšné plné kompilaci je ještě nutné
ověřit velikost binárního souboru a před OTA porovnat rozložení s firmwarem skutečně
nahraným v zařízení. Změna či vymazání NVS může zrušit HomeKit/HomeKey párování.



## Přímé zdroje

- [HAP-ESPHome README](https://github.com/rednblkx/HAP-ESPHome/tree/0ab12c97f33d894909a35b24b9e837384d063861)
- [Pevně zvolený Wi-Fi transport](https://github.com/rednblkx/HAP-ESPHome/blob/0ab12c97f33d894909a35b24b9e837384d063861/components/homekit_base/HAPRootComponent.cpp)
- [Zařazení MFi I2C souboru do sestavení](https://github.com/rednblkx/esp-homekit-sdk/blob/1d1ea30bba62ed9c9d55da6613d828a658ec2a39/components/homekit/esp_hap_platform/CMakeLists.txt)
- [Chybějící větev pro ESP32-P4](https://github.com/rednblkx/esp-homekit-sdk/blob/1d1ea30bba62ed9c9d55da6613d828a658ec2a39/components/homekit/esp_hap_platform/src/esp_mfi_i2c.c)
- [Rozlišení Ethernetu v SDK](https://github.com/rednblkx/esp-homekit-sdk/blob/1d1ea30bba62ed9c9d55da6613d828a658ec2a39/components/homekit/esp_hap_core/src/esp_hap_wifi.c)
- [Úložiště NVS](https://github.com/rednblkx/esp-homekit-sdk/blob/1d1ea30bba62ed9c9d55da6613d828a658ec2a39/components/homekit/esp_hap_core/src/esp_hap_keystore.c)
- [Schéma desky, P6 na prvním listu](https://files.waveshare.com/wiki/ESP32-P4-WIFI6-POE-ETH/ESP32-P4-WIFI6-POE-ETH-Schematic.pdf)
