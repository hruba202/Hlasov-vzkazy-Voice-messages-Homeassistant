# Etapa 1 – HuskyLens a úklid

Celý výsledný YAML je v `esp32p4.yaml`. Lokální externí komponenta je v
`components/huskylens_bridge/`; při kopírování do ESPHome přeneste také tuto složku
vedle YAML. Původní `huskylens_bridge.h` byl dodán dodatečně a zůstává jako reference;
aktivní je nová implementace externí komponenty.

Dodaná deska je **Waveshare ESP32-P4-WIFI6-POE-ETH**, podle aktuální dokumentace
výrobce s 32 MB NOR flash a C6-MINI-1U-H8. Není to P4-NANO; dřívější poznámka
o 16 MB flash se týkala jiného modelu. Hodnota 32MB ve výsledném YAML je zachována.

Dodatečně přiložený header už nepoužívá Arduino Wire, ale přímo starý ESP-IDF I2C
ovladač s natvrdo vybraným portem 0. Neregistruje instanci do ESPHome, čte jen první
16bytový rámec a očekává chybný příkaz 0x05. U V1 přitom požadavek vrací nejdřív
informační rámec 0x29 a potom bloky 0x2A. Nová implementace řeší i tyto chyby.

## Odpovědi před implementací

- **BLE proxy:** podpora BLE přes ESP-Hosted přibyla v ESPHome 2025.11.
  Vaše verze nebyla uvedena a nelze ji zjistit z YAML. Pro ověření první etapy
  používám ESPHome 2026.9.0; nejde o potvrzení kompatibility HAP-ESPHome s touto verzí.
  Pro BLE musí firmware C6 podporovat Bluetooth a odpovídat hostiteli.
  Alternativou je samostatná ESP32 BLE proxy s vlastním API připojením.
- **C6:** u P4-NANO slouží jako Wi-Fi/BT koprocesor přes SDIO. Ethernet jej
  pro přenos dat nepotřebuje, ale P4 jej potřebuje pro bezdrátové funkce.
  Nahrání vašeho Zigbee firmwaru nahradí ESP-Hosted; běžné dva samostatné firmwary
  nelze provozovat současně. Podrobný návrh Zigbee ponechávám až do etapy 5.
- **HomeKey:** README požaduje ESP-IDF 5 a upravené PN532/SPI komponenty z repozitáře.
  Použít `homekit.lock[].nfc_id`, vazbu na template lock a úspěšnou autentizací
  přepínat stav podle předlohy. Vyžaduje skutečnou PN532 čtečku zapojenou přes SPI.
  Přidat `CONFIG_COMPILER_OPTIMIZATION_SIZE: y`, `CONFIG_LWIP_MAX_SOCKETS: "16"`
  a `CONFIG_MBEDTLS_HKDF_C: y` do `esp32.framework.sdkconfig_options`.
  Funkční P4 + Ethernet nelze z README potvrdit. Kód deklaruje závislost na obecné
  síti a mDNS, takže Ethernet je pravděpodobná cesta, nikoli ověřený výsledek.
  Ověřit bude třeba kompilaci všech závislostí, mDNS, párování a autentizaci.
  README nepředepisuje speciální partition table; před OTA ověřit skutečnou flash,
  velikost aplikace a oba OTA oddíly. Zatím vlastní tabulku nevytvářím.
- **Piny NFC:** TODO_OVERIT_SPI_CLK, TODO_OVERIT_SPI_MISO,
  TODO_OVERIT_SPI_MOSI, TODO_OVERIT_PN532_CS. Jsou to dokumentační placeholdery,
  nejsou aktivní konfigurací. Bez přesného modelu a schématu nelze bezpečně přiřadit
  GPIO ani čísla kontaktů 40pin headeru. Nekopírovat SPI GPIO z předlohy S3.
- **Verze:** doporučený kandidát pro první etapu je 2026.9.0, výchozí ESP-IDF dodaný
  touto verzí. Pro HomeKey musíme později ověřit současně kompatibilní vydání
  ESPHome, ESP-IDF 5.x a konkrétní revizi HAP-ESPHome. Samotné vynucení starého
  ESP-IDF 5.0 na P4 není řešení.

## Změny

- Pryč jsou MQTT včetně přihlašovacích údajů, nepoužitý mikrofon,
  `init_in_progress`, chybějící include a interval s ručním `setup()`.
- Žádný voice_assistant v původním YAML nebyl. Media player a audio zůstaly;
  jejich piny jsou označeny jako neověřené a oprava patří do etapy 2.
- Nová komponenta dědí z `PollingComponent` a `i2c::I2CDevice`, používá `bus_a`,
  GPIO7/GPIO8 a adresu 0x32. Nezávisí na Arduino/Wire.
- Požadavek na bloky každých 250 ms. Odpovědi se zpracovávají po 16 bytech
  s rozestupy alespoň 5 ms bez čekací smyčky, s limitem 150 ms a kontrolou checksumu.
  Všechny bloky odpovědi se přečtou před zveřejněním prvního z nich.
  Limit je 64 bloků; neúplná nebo chybná odpověď je chyba komunikace.
- Šest template senzorů se aktualizuje po 250 ms. ID a Command mají delta 0.5,
  geometrie delta 2.0. Command je pro obdélníkovou detekci 42 (0x2A).
  Výběr prvního bloku není sledování stejného objektu mezi snímky; ID může být 0
  pro nenaučený objekt. Šipky se tímto požadavkem nezískávají.
- Bez objektu nebo při chybě vracejí čísla NaN. Presence má lambda a při chybě
  přejde na false. Od skutečné absence ji rozliší nový diagnostický senzor
  Communication OK. Po obnovení komunikace se stav automaticky obnoví.
- API klíč zůstává přes `!secret esp_encryption_key`; přidáno OTA heslo přes
  `!secret ota_password`. Skutečná tajemství se nevytvářejí.

## Co ověřit před nahráním

1. Revizi desky a verzi ESPHome.
   Identifikátor `esp32-p4-evboard` není důkaz konkrétní Waveshare varianty.
   Aktuální dokumentace WIFI6-POE-ETH uvádí 32 MB flash, což odpovídá YAML;
   pro fyzický kus ji lze potvrdit z detekce flash při připojení.
2. Zda jde o HuskyLens V1 a v jeho menu je zvolen protokol I2C.
   Ověřit napájení, společnou zem a bezpečné 3.3V úrovně/pull-upy sběrnice.
3. I2C scan musí najít 0x32. Případné 0x18 patří ES8311.
4. V HA ověřit prázdný obraz, jeden i více bloků, změnu ID, pohyb, rozměry,
   odpojení kamery a její opětovné připojení. Číselné hodnoty nesmějí zůstat staré
   při chybě; Communication OK musí zhasnout a po návratu se rozsvítit.
5. Audio ještě není opravené. Před použitím ověřit I2S, MCLK a zesilovač ve schématu.
   Ani Ethernet GPIO nebyla změněna; vstupní mapování je třeba potvrdit pro revizi.

## Zdroje

- https://esphome.io/blog/2025/11/19/esphome-2025-11/
- https://esphome.io/blog/2026/09/16/esphome-2026-9/
- https://esphome.io/components/esp32_hosted/
- https://esphome.io/components/bluetooth_proxy/
- https://github.com/rednblkx/HAP-ESPHome
- https://github.com/rednblkx/HAP-ESPHome/blob/main/components/homekit_base/__init__.py
- https://www.waveshare.com/wiki/ESP32-P4-Nano-StartPage
- https://docs.waveshare.com/ESP32-P4-WIFI6-POE-ETH
- https://github.com/HuskyLens/HUSKYLENSArduino/tree/master/HUSKYLENS
- https://esphome.io/components/external_components/
- https://esphome.io/components/sensor/#delta

Po etapě 1 se práce zastavuje podle zadání. Etapy 2–5 nejsou implementovány.

## Provedené ověření

ESPHome 2026.9.0 úspěšně validoval celý výsledný YAML s lokální komponentou.
Pro kontrolu byla použita dočasná kopie s testovacími tajemstvími, protože skutečný
`secrets.yaml` nebyl dodán. Výchozí framework této verze se vyhodnotil jako ESP-IDF
5.5.5. Úspěšně prošlo i generování C++ zdrojů (`compile --only-generate`).
Úplná kompilace firmware ani zkouška na hardwaru provedena nebyla.
