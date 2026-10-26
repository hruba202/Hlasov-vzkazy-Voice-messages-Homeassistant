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

## Postup na desce

1. Použijte vlastní `secrets.yaml` s API klíčem a OTA heslem stávajícího
   zařízení. Sestavte tuto variantu; nenahrávejte binárku s dočasnými údaji
   z lokálního ověření.
2. Zastavte přehrávání a počkejte na uvolnění reproduktoru. Pouhé ztlumení
   ani pozastavení nemusí uvolnit I²S. Během testu nespouštějte hudbu ani
   automatická hlášení; nová varianta neblokuje příkazy zaslané přehrávači.
3. Stiskněte **Mikrofon test 30 s**. Mluvte z malé vzdálenosti a poté
   z obvyklé vzdálenosti návštěvy u dveří. Porovnejte s tichem.
4. `Mikrofon snima` má přejít na zapnuto a RMS/Peak se mají přibližně jednou
   za sekundu měnit podle zvuku. Hodnoty jsou relativní digitální úroveň
   v dBFS, nikoli kalibrované dB SPL, i když standardní komponenta používá
   jednotku dB. Méně záporná hodnota znamená silnější signál; 0 dBFS je
   digitální maximum. Častý Peak blízko 0 ukazuje možné přebuzení.
5. Po 30 sekundách má snímání skončit. Ověřte také předčasné zastavení
   tlačítkem a opakovaný start. Pak ověřte obnovené přehrávání hudby.
6. Po celou dobu sledujte obraz kamery a hodnoty HuskyLens. Úspěšná kompilace
   nepotvrzuje jejich stabilní souběh se snímáním.

Očekávané vlastní zprávy logu:

```text
D1: spoustim mikrofon 48000 Hz / 16 bit / levy kanal
D1: mikrofon bezi, test 30 sekund
D1: konec testu, uvolnuji I2S
```

V klidu může komponenta `sound_level` hlásit
`Microphone isn't running, can't compute statistics` a senzory budou
nedostupné. To je při záměrně vypnutém mikrofonu očekávané.
Indikace „snímá“ potvrzuje běh ovladače; příjem skutečného zvuku potvrdí až
reakce RMS/Peak. Pokud jsou stále stejné nebo bez hodnot, pošlete log od
startu testu. Levý kanál a zisk zatím nejsou prakticky potvrzené.

## Ověření sestavení

Výsledky sestavení jsou v `investigation/microphone/`. Použitý nástroj:
ESPHome 2026.9.0, ESP-IDF 5.5.5. Na uživatelově desce dosud běží 2026.9.1.
Validace `esphome config`, generování C++ i plná kompilace úspěšně prošly.
První pokus o kompilaci zastavilo síťové omezení prostředí; opakovaný běh
s přístupem ke stažení veřejných závislostí skončil úspěšně.

| Výsledek | Hodnota |
|---|---:|
| OTA binárka | 1 211 232 B |
| Factory binárka | 1 276 768 B |
| Obraz aplikace podle size | 1 210 824 B, 7,3 % aplikačního oddílu |
| Statická interní DIRAM | 106 482 / 576 464 B, 18,5 % |
| Statické sekce External RAM | 1 130 268 B |

External RAM v sestavovacím výpisu zahrnuje sekce programu při XIP;
nejde o změřenou dynamickou spotřebu PSRAM. Procento tohoto výpisu má
jmenovatel podle adresního prostoru, nikoli podle fyzických 32 MiB desky.
Paměť za běhu a funkčnost mikrofonu na desce dosud změřené nejsou.

Vyřešené závislosti jsou zachycené v `investigation/microphone/dependencies.lock`:
esp_video 2.3.0, usb_host_uvc 2.5.2, esp_cam_sensor 2.3.0, esp_ipa 2.2.0~1,
esp_h264 1.3.0, esp_sccb_intf 1.0.0, cmake_utilities 0.5.3, mdns 1.12.0,
esp-audio-libs 3.2.1, micro-flac 0.2.0, IDF 5.5.5. Lokální noise-c a
libsodium mají v locku verzi `*`. SCCB se proti staršímu sestavení kamery
vyřešilo nově na 1.0.0; samotné připnutí kamerové komponenty nezamyká všechny
její tranzitivní závislosti. Kamera nadále používá stejný připnutý commit.

Kontrola hashů potvrdila nezměněné všechny tři původní YAML soubory
(`investigation/microphone/preservation-check.json`). Kompilace používala
dočasný API klíč a OTA heslo; dočasný `secrets.yaml` byl odstraněn.
Vzniklé binárky jsou pouze dokladem kompilace: před nasazením sestavte
znovu s vlastními přístupovými údaji. Nic nebylo flashováno.

Zapojení a zdroje: [posouzení D](ETAPA_D_MIKROFON.md).
Hardwarové možnosti desky nejsou omezené na tento test; souběžný příjem
a přehrávání závisí i na implementaci firmware. Zde používáme střídání
směrů kvůli zamykání společné sběrnice v místní verzi ESPHome.

## Výsledek testu na desce dodaný uživatelem

Log z 21. 10. 2026 potvrzuje start v 17:30:51.882 a ukončení v 17:31:21.884.
Byl vytvořen buffer 11 520 B a průběžně publikovány RMS/Peak; například
RMS −35,6 až −38,8 dBFS, Peak nejprve −5,1 dBFS a dále přibližně −20 až
−24 dBFS. Kamera současně hlásila snímky 1280×720. Po ukončení se objeví
očekávané varování o vypnutém mikrofonu a hodnota `nan`.

To potvrzuje příjem vzorků, výpočet úrovně a ukončení testu při souběhu
s kamerou. Bez označených úseků řeči/ticha nebo poslechu nahrávky samotný
log nepotvrzuje srozumitelnost hlasu, optimální zisk ani dlouhodobou stabilitu.
Následuje [D2 — uložení krátkého záznamu](ETAPA_D2_VZKAZY.md).
