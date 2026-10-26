# ESP32-P4: USB kamera, audio a HuskyLens

Experimentální projekt ESPHome pro **Waveshare ESP32-P4-WIFI6-POE-ETH**:

- USB kamery přes USB-A (UVC/MJPEG), obraz v Home Assistantu.
- Přehrávání audia přes ES8311 a `media_player`.
- HuskyLens V1 přes I2C, vlastní komponenta `huskylens_bridge`.
- Ethernet IP101; HomeKey zůstává na samostatném ESP32, BLE proxy není součástí.

## Konfigurace

| Soubor | Účel |
|---|---|
| `esp32p4.yaml` | Základ: Ethernet, HuskyLens a audio |
| `esp32p4-camera.yaml` | USB kamera 640×480, limit 10 fps |
| `esp32p4-camera-720p.yaml` | USB kamera 1280×720, limit 10 fps |
| `esp32p4-microphone-test.yaml` | D1: ručně spouštěný 30s test mikrofonu, dědí kameru 720p |
| `esp32p4-voice-message.yaml` | D2: 10s hlasový vzkaz pro přijímací doplněk v HA OS |
| `esp32p4-assist-message.yaml` | D3: standardní Assist a textový vzkaz bez přijímacího doplňku |

Varianty používají `packages`, proto zachovejte všechny tři YAML soubory
a adresář `components/`. Kamera je připnutá na commit
`53a315e76c69178d913e6744314408a98bc87234` z
[youkorr/esphome](https://github.com/youkorr/esphome/tree/53a315e76c69178d913e6744314408a98bc87234/esphome/components/esp_video_camera).
Lokální `camera_log_compat` doplňuje kompatibilitu logování pro ESPHome 2026.9.0.

## Spuštění

Vytvořte vlastní `secrets.yaml` (nepatří do Gitu):

```yaml
esp_encryption_key: "SEM_VLOZTE_VLASTNI_API_KLIC"
ota_password: "SEM_VLOZTE_VLASTNI_OTA_HESLO"
```

API klíč musí být platný 32bajtový klíč v Base64. Potom ověřte a sestavte
zvolenou variantu, například:

```sh
esphome config esp32p4-camera-720p.yaml
esphome compile esp32p4-camera-720p.yaml
```

Firmware nahrajte až po úspěšné kompilaci a zařízení přidejte přes ESPHome
integraci v Home Assistantu. Dřívější lokální binárky s testovacími údaji
nejsou určené k nasazení. Varianty sdílejí build adresář; výstupní binárky
patří vždy poslednímu sestavení.

## Ověřený stav

- Plná kompilace: ESPHome **2026.9.0**, ESP-IDF **5.5.5**.
- Test na desce: ESPHome **2026.9.1**, P4 rev1.3, 32 MB PSRAM.
- **Jelly Comb (1BCF:28C4, ve Windows FHD Camera)**: na této kameře
  proběhlo celé dosavadní testování a pocházejí z ní uvedené logy a fps.
- **Nulaxy (0C45:636B, ve Windows USB 2.0 Camera)**: samostatně otestovaná
  uživatelem, funguje bez hlášených problémů; vlastní měření fps není doloženo.
- **Logitech C270 (046D:0825) zatím nefunguje**: host při pokusech hlásí
  `0 USB device(s) on the bus`. Příčina nerozpoznání není zatím určená.
- VGA: uživatelem ověřen současný obraz, přehrávání hudby a načítání HuskyLens.
- 720p: funkční obraz, v dodaném logu **8,1–9,8 fps**. Dlouhodobý souběh
  s audiem a HuskyLens v tomto režimu zatím není doložen.

Původní přiřazení úspěšných testů Logitechu bylo nesprávné; uživatel
21. 10. 2026 výslovně přiřadil celé dosavadní testování k Jelly Comb.

`max_framerate` omezuje předávání do HA, nikoli frekvenci přenosu USB kamery.
Nepřidávejte `usb_host`: použitá UVC komponenta spravuje USB host sama.
Sestavení používá `esp_video 2.3.0` a `usb_host_uvc 2.5.2`; tato verze nemá
opravu [#571](https://github.com/espressif/esp-usb/pull/571), takže funkčnost
s jinými kamerami nebo režimy není zaručená.

Podrobnosti a výsledky jsou v [reportu B](ETAPA_B_KAMERA.md)
a [reportu C](ETAPA_C_KAMERA.md). Starší HomeKey návrhy jsou pouze historické
podklady a nejsou součástí aktuální kamerové konfigurace.

## Vznik projektu

[Etapa D — mikrofon na desce](ETAPA_D_MIKROFON.md) posuzuje živý poslech
a záznam zvuku. [První fáze D1](ETAPA_D1_TEST.md) přidává ruční test úrovně
zvuku. [D2 — hlasové vzkazy](ETAPA_D2_VZKAZY.md) přidává samostatnou variantu
firmware a přijímací doplněk pro HA OS; instalace a záznam na skutečné desce
dosud nejsou ověřené.

Aktuální směr je [D4 — dveřní P4 do existujícího VoIP Stacku](ETAPA_D4_INTERKOM.md).
Nová varianta `esp32p4-intercom.yaml` prošla validací i plnou kompilací;
obousměrný hovor na této P4 čeká na test. Kamera a HuskyLens zůstávají zachované.

Předchozí alternativa pro textové vzkazy je v [posouzení D3: text a hlas přes Assist](ETAPA_D3_ASSIST_POSOUZENI.md).
Používá vestavěnou akci `ask_question`, textový archiv a volitelné diagnostické WAV.
[Připravená varianta D3 a postup nasazení](ETAPA_D3_PRIPRAVA.md) obsahuje nový YAML,
lokální převod mikrofonu 48 → 16 kHz a skript HA. Živý test Assistu na desce zatím neproběhl.

Projekt vznikl ve spolupráci s **ChatGPT / Codex od OpenAI**. AI pomáhala
s průzkumem, konfigurací, implementací komponent a ověřením kompilace;
funkčnost na skutečném hardwaru ověřoval autor projektu.
