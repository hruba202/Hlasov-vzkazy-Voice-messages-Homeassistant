# D4 — dveřní P4 do existujícího VoIP Stacku

## Oprava pro ESPHome 2026.10.0

Dokončení opravy ověřeno 24. 10. 2026: **validace i plná kompilace na
ESPHome 2026.10.0 a ESP-IDF 5.5.5 prošly**. Výsledek je zaznamenán v
`investigation/intercom/config.log` a `compile.log`.

- OTA: **1 444 096 B**; factory: **1 509 632 B**.
- Interní statická RAM: **109 064 / 576 464 B (18,9 %)**.
- Obraz podle linkeru: **1 443 694 B (8,7 % oddílu)**.
- Živá spotřeba PSRAM a funkčnost hovoru na desce zatím nejsou ověřené.
- Původní konfigurace zůstaly beze změn, dočasné secrets byly odstraněny.
- Nic nebylo flashováno; kontrolní binárky s testovacími údaji nepoužívat.


Uživatelův log odhalil nekompatibilitu připnutého Audio Stacku s ESPHome
2026.10.0: `RingBuffer::handle_` se změnilo z datového členu na metodu.
Původní úspěšná kompilace na 2026.9.0 tuto změnu nemohla odhalit.
Aktuální hlavní YAML proto připíná pouze komponentu `ring_buffer` k oficiální
revizi ESPHome 2026.9.0 `c6e4c87e525dd343e470d8dea368957a002f6505`.
Nejde o downgrade celé instalace ESPHome ani změnu pinů nebo parametrů zvuku.
Je to dočasná kompatibilní varianta pro tuto konkrétní revizi Audio Stacku.

Pro již rozbalený balíček stačí nahradit `esp32p4-intercom.yaml` jeho aktuální
verzí. V ESPHome Device Builderu doporučujeme u zařízení jednou zvolit
**Clean Build Files / Vyčistit soubory sestavení** a poté znovu kompilovat.
`esp32p4-intercom-base.yaml`, místní komponenty a vlastní secrets neměnit.

Připraveno 22. 10. 2026. Validace a plná kompilace prošly. Na desku se nic
nenahrávalo a konfigurace Home Assistanta se neměnila. Funkčnost hovoru na této
P4 se musí teprve ověřit; uživatel již ověřil své ostatní ESP ↔ ESP a ESP ↔ panel.

## Co použít

- `esp32p4-intercom.yaml` — hlavní konfigurace, kompilovat tento soubor.
- `esp32p4-intercom-base.yaml` — jeho základ, musí ležet vedle něj.
- `components/huskylens_bridge/` a `components/camera_log_compat/` — místní komponenty.
- Vlastní `secrets.yaml` s dosavadními `esp_encryption_key` a `ota_password`.

Vše kromě secrets je v `D4-intercom-package.zip`. Rozbalit do adresáře konfigurací
ESPHome; zachovat strukturu `components`. Nevkládat YAML do konfigurace HA.
Nekombinovat s D1/D2/D3 mikrofonními variantami: každá má jiného vlastníka zvuku.
Žádný nový přijímací doplněk ani další instalace VoIP Stacku nejsou potřeba.

## Co se změnilo

Původní `esp32p4.yaml`, VGA a 720p YAML jsou beze změny (ověřeno SHA256).
Nový základ je kopií původního, ze které jsou odstraněny původní I2S, ES8311
a hardwarový speaker. Kontrola zapnutí zesilovače nyní odkazuje na `door_audio`.
Tyto části přebírá existující komponenta `esp_audio_stack`, aby současně
obsluhovala oba směry sdílené I2S sběrnice. Nelze současně nechat původní
ES8311 ovladač a nový ovladač řídit tentýž kodek.

HuskyLens, Ethernet, I2C i blok `media_player` jsou převzaté beze změn.
Přehrávač stále používá `box_speaker`, ale tento výstup je nyní samostatný vstup
mixeru. Hovor má druhý vstup. Při volání nebo příchozím vyzvánění se dosavadní
přehrávání zastaví; automaticky se neobnovuje. Chování hlasitosti je nutné
znovu ověřit, protože se změnil ovladač reproduktoru.

Zapojení zůstává MCLK13, BCLK12, LRCLK10, mikrofon DIN11, reproduktor DOUT9,
zesilovač GPIO53, analogový ES8311 na I2C 0x18. Zvuk je 48 kHz / 16 bit / mono,
VoIP používá PCM, signalizaci UDP 5060 a RTP 40000. ESPHome API poskytuje
automatické objevení telefonu a ovládací akce. Název zařízení zůstává ESP32-P4.

USB kamera je stejná jako v etapě C: 1280×720, limit 10 fps, USB mapa 0x01.
Obraz je samostatně dostupný v HA; tato varianta neposílá video v SIP hovoru.
Není přidán Assist, BLE ani HomeKey. Detekce obličeje zatím sama nevolá a nic
neodemyká. Snímek a automatické vyzvánění navážeme až na ověřený ruční hovor.

## První test na desce

1. Ve svém ESPHome zkompilovat `esp32p4-intercom.yaml` s vlastními secrets.
   Zde vytvořené binárky jsou pouze kontrolní, obsahují náhodné testovací
   přístupové údaje a nejsou určeny k nasazení.
2. Po úspěšném sestavení lze uživatelsky nahrát firmware. Zachovat si předchozí
   funkční konfiguraci pro návrat. Agent nic neflashoval.
3. Zkontrolovat Ethernet, obraz kamery a hodnoty HuskyLens. V logu nemají být
   chyby inicializace ES8311/I2S ani nedostatek paměti.
4. Ve stávajícím VoIP Stacku vyhledat ESP32-P4. V kartě vybrat existující
   zařízení ESPHome; nezakládat druhé zařízení se stejnou identitou.
5. Zavolat z funkčního druhého ESP na P4. Automatický příjem je standardně
   vypnutý. Hovor přijmout kartou nebo tlačítkem
   „Interkom volat prijmout zavesit“. Pro ruční test lze zapnout
   „Interkom automaticky prijem“. „Interkom nerusit“ a ztlumení mikrofonu
   musí být vypnuté.
6. Ověřit oba směry řeči. Zařízení umístit do různých místností, začít s nízkou
   hlasitostí. Tato první varianta neobsahuje AEC: ozvěna může nastat a samotný
   úspěch kompilace ji nevylučuje. Při zpětné vazbě snížit hlasitost / ukončit hovor.
7. Zkusit opačný směr přes výběr kontaktu a tlačítko volání na P4. Hovor ukončit,
   znovu zavolat a nakonec ověřit přehrávání zprávy přes `p4_player`.
8. Zopakovat hovor při běžícím obrazu kamery a sledovat výpadky zvuku, fps a HuskyLens.

V aktivním hovoru očekáváme vlastní zprávu `D4: hovor aktivni`, při ukončení
`D4: konec hovoru: ...`. „Interkom diagnostika“ vypíše diagnostiku komponenty.
Při problému dodat log od startu zařízení a obou konců hovoru; zvláště vyjednaný
zvukový formát a počítadla RTP. Kompatibilita s konkrétní revizí firmware druhého
ESP a instalovanou HA integrací se potvrdí až tímto testem. HTTPS panel ↔ panel
není součástí této etapy.

## Původní výsledky sestavení na ESPHome 2026.9.0

ESPHome 2026.9.0, ESP-IDF 5.5.5. `esphome config` i plná kompilace úspěšné.

| Položka | Výsledek |
|---|---:|
| OTA binárka | 1 464 176 B |
| Factory binárka | 1 529 712 B |
| Velikost obrazu podle linkeru | 1 463 780 B (8,9 % aplikačního oddílu) |
| Statická interní RAM | 111 106 / 576 464 B (19,3 %) |
| Statické sekce External RAM | 1 383 136 B |

External RAM zahrnuje sekce přesunuté pomocí XIP, nikoli živou spotřebu kamery,
zvukových bufferů a haldy. Linker uvádí adresní prostor 128 MiB, ne skutečnou
kapacitu desky. Volnou fyzickou PSRAM a zatížení CPU při hovoru zatím neměříme.

Sestavení hlásí upozornění na příliš vysoké výchozí lwIP hodnoty ESPHome
(512 mailbox, TCP window 512000); IDF je odmítá a použije povolené výchozí hodnoty.
Dále jsou upozornění na zastaralé ISP konstanty a nepoužitou pomocnou funkci.
Žádná z těchto hlášek sestavení nezastavila. Podrobnosti:
`investigation/intercom/compile.log`, `dependencies.lock`, `versions.json`.

## Připnuté zdroje a skutečné závislosti

- [esp_audio_stack](https://github.com/n-IA-hane/esphome-audio-stack/tree/0482d741a938378ef948e3b8f3dd31536f9f2cc9): `0482d741a938378ef948e3b8f3dd31536f9f2cc9`.
- [voip_stack](https://github.com/n-IA-hane/esphome-voip-stack/tree/c693b4e75008afb5d2f584a09035aee2743a2210): `c693b4e75008afb5d2f584a09035aee2743a2210`.
- [esp_video_camera](https://github.com/youkorr/esphome/tree/53a315e76c69178d913e6744314408a98bc87234/esphome/components/esp_video_camera): `53a315e76c69178d913e6744314408a98bc87234`.
- Referenční [esphome-intercom](https://github.com/n-IA-hane/esphome-intercom/tree/6581cfea712d0e13bf88c5aff3fa97b9e27123ab): `6581cfea712d0e13bf88c5aff3fa97b9e27123ab`.

Z `dependencies.lock`: esp_codec_dev **2.0.0-beta5**, esp_audio_effects **1.3.0~1**,
gmf_fft **1.0.0**, esp_video **2.3.0**, usb_host_uvc **2.5.2**, usb_host_uac **1.5.0**,
esp_cam_sensor **2.3.0**, esp_h264 **1.3.0**, esp_ipa **2.2.0~1**,
esp_sccb_intf **1.0.0**, cmake_utilities **0.5.3**, mdns **1.12.0**,
esp-audio-libs **3.2.1**, micro-flac **0.2.0**, IDF **5.5.5**.
libsodium a noise-c jsou lokální komponenty s verzí `*`.
UAC je tranzitivní závislost codec_dev; konfigurace používá analogový mikrofon
ES8311, nikoli USB mikrofon. ESPHome `usb_host` se nepřidává.

## Co ještě není hotové

Nahrávání hlasových vzkazů, automatická výzva po nezvednutí a automatizace
snímek/vyzvánění nejsou touto variantou implementovány. VoIP Stack sám nemá
hlasovou schránku — viz [dokumentace](https://github.com/n-IA-hane/esphome-intercom/blob/6581cfea712d0e13bf88c5aff3fa97b9e27123ab/docs/AUTOMATION_DIALPLAN.md#L1275).
Tato etapa připravuje konkrétně připojení dveřní P4 k existujícím telefonům.

Konfiguraci a ověření kompilace připravil ChatGPT / Codex od OpenAI s využitím
projektů n-IA-hane. Jejich komponenty nejsou naše vlastní implementace.
