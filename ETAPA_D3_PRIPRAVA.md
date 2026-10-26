# D3 — připravená varianta Assist pro vzkazy

Datum: 22. 10. 2026. Navazuje na [posouzení možností](ETAPA_D3_ASSIST_POSOUZENI.md).
Firmware: `esp32p4-assist-message.yaml`. Skript HA: `home_assistant/door_message_script.yaml`.

## Co se změnilo

Nový YAML dědí kameru 720p, Ethernet, HuskyLens a přehrávač. Nemění původní
YAML soubory ani nastavení přehrávání. Přidává mikrofon GPIO11 se stejnými
parametry jako D1, lokální adaptér `mic_48_to_16` a standardní `voice_assistant`.
Zisk mikrofonu je jako v D1 24 dB. Nepoužívá HTTP přijímač, jeho token ani
adresu, nepotřebuje repozitář doplňku a nevyužívá ESP32-C6.

Převod 48 → 16 kHz je na desce. Ověřeno v místním ESPHome 2026.9.0:
`voice_assistant/__init__.py:196` vyžaduje 16 kHz;
`voice_assistant.cpp:21` používá pevnou frekvenci 16 kHz;
`microphone/microphone_source.h` výslovně nepřevádí frekvenci.
HA Core 2026.10.2 v `assist_satellite/entity.py:515` nastavuje příjem na 16 kHz.
Proto prosté odeslání 48kHz proudu není správný postup. Obecná schopnost
HA převzorkovat jiná média tento konkrétní přenosový kontrakt nemění.

Adaptér používá 63koeficientový FIR dolní propust (Hamming, mez 6,5 kHz,
Q15) a vybírá každý třetí filtrovaný vzorek. Zachovává stav filtru, fázi
i rozpracovaný bajt mezi bloky. Nezapisuje do flash, neukládá celý vzkaz.
Výpočet je přibližně 1 milion násobení/s; skutečné vytížení CPU se musí změřit.

## Soubory pro ESPHome

Do stejného adresáře v ESPHome patří:

```text
esp32p4-assist-message.yaml
esp32p4-camera-720p.yaml
esp32p4-camera.yaml
esp32p4.yaml
secrets.yaml                  # tvoje stávající údaje, ne součást distribuce
components/
  mic_48_to_16/               # celý adresář
  huskylens_bridge/
  camera_log_compat/
```

Zůstávají jen původní secrets `esp_encryption_key` a `ota_password`.
`voice_receiver_ip` a `voice_receiver_token` z experimentu D2 tato varianta
nepoužívá. Nový firmware má vlastní build adresář.

```sh
esphome config esp32p4-assist-message.yaml
esphome compile esp32p4-assist-message.yaml
```

Nasazovat až po plné kompilaci s vlastními secrets. Lokální binárky pro
ověření používají dočasné údaje; agent nic neflashuje.

## Nastavení a první textový vzkaz v HA

1. Po nasazení nové varianty ověřit u zařízení novou entitu `assist_satellite`.
   Její skutečné ID vyberete z nabídky, žádné předem odhadnuté není nutné.
2. U satelitu zvolit existující českou Assist pipeline. Musí mít funkční STT
   a pro textovou výzvu také TTS. Pokud TTS není nastavené, nejprve jej doplnit
   nebo upravit otázku na `question_media_id` s vlastní nahranou výzvou.
3. **Nastavení → Automatizace a scény → Skripty → Vytvořit nový skript**,
   otevřít editor YAML a vložit celý obsah `home_assistant/door_message_script.yaml`.
   Jde o obsah jednoho skriptu v UI, nikoli celý soubor `scripts.yaml`.
4. Spustit skript s vybraným dveřním satelitem a přehrávačem téže desky.
   Pole archivu nechat pro první pokus prázdné. Pokud UI nenabídne vyplnění
   polí při spuštění, použít Vývojářské nástroje → Akce, vybrat nově uložený
   skript a vyplnit jeho pole tam.
5. Skript zastaví hudbu, přehraje výzvu a čeká na krátkou odpověď. Po řeči
   udělejte pauzu. V oznámeních HA se má objevit přepis s časem.
6. Ověřit v ladění pipeline, že zpracování končí STT a nenásleduje intent.
   Nepoužívat pro příjem vzkazů běžné `voice_assistant.start` ani
   `assist_satellite.start_conversation` místo připravené akce otázky.

`ask_question` bez `answers` vrací volný přepis. V tomto režimu HA ukončí
pipeline po STT; vzkaz se nevyhodnocuje jako příkaz domu. Není zapnutý wake
word ani nepřetržité naslouchání. To platí pro připravený skript, nikoli
libovolné jiné automatizace, které by uživatel později doplnil.
Zdroj: [akce otázky](https://www.home-assistant.io/actions/assist_satellite.ask_question/)
a [implementace HA](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/components/assist_satellite/entity.py).

K dispozici je tlačítko **Vzkaz zastavit**. Firmware má navíc ochranný limit
45 sekund od startu pipeline. Konec řeči může přijít dříve podle VAD v HA;
nejde o přesně 45sekundový rekordér. Po celou dobu nepouštět další hudbu
ani hlášení do stejného přehrávače. Skript dřívější hudbu automaticky neobnovuje.

## Volitelné trvalé ukládání textu

Pro první test stačí oznámení. Pro archiv vytvořit adresář `/config/vzkazy`
a povolit jej v existující sekci `homeassistant` konfigurace HA:

```yaml
homeassistant:
  allowlist_external_dirs:
    - /config/vzkazy
```

Sloučit s existující konfigurací, nepřepsat jiné položky. Po kontrole
konfigurace a restartu přidat v **Zařízení a služby → Integrace → File**
oznamovací entitu pro `/config/vzkazy/navstevy.jsonl`. Pokud integrace nabízí
vlastní časové razítko, nechat vypnuté: připravený skript ukládá čas do JSON.
Tuto notify entitu vybrat v poli archivu při spuštění skriptu.

Každý úspěšný vzkaz se připojí jako JSON řádek. Nové řádky a uvozovky v řeči
se serializují, obsah se nikdy nevkládá do shellového příkazu. Přepis se
nezkracuje na limit stavového senzoru. Soubor není automaticky rotovaný;
jeho archivaci/velikost bude potřeba řešit při běžném provozu.
Zdroj: [File](https://www.home-assistant.io/integrations/file/).

## Volitelný poslech původního hlasu

Připravený soubor `home_assistant/assist_debug_recording.example.yaml`
obsahuje diagnostické ukládání do `/media/assist_debug`. Sloučit jej
s konfigurací HA, ověřit a restartovat HA. Po dalším vzkazu hledat WAV
v **Média → Moje média → assist_debug**, v podadresáři běhu.

Je to globální diagnostika: může zaznamenávat i další satelity, soubory
automaticky nemaže a nemá přímé propojení s textovým oznámením. Po ověření
kvality ji vypnout a HA restartovat. Přístup ke skutečnému umístění a
přehrání je potřeba potvrdit v dané instalaci HA OS. Oficiální návod používá
`/share/assist_pipeline`; zde je navržena stejná funkce s cestou do médií.
Zdroj: [diagnostické nahrávky Assist](https://www.home-assistant.io/voice_control/troubleshooting/).

## Kontroly a stav

Validace ESPHome, generování C++ a plná kompilace **prošly** s ESPHome 2026.9.0
a ESP-IDF 5.5.5. Lokální pokus s přímým 48kHz zdrojem byl podle očekávání
odmítnut validací; log je v `investigation/assist-message/rejected-48khz.log`.
Oba YAML soubory pro HA prošly načtením YAML; nejde o validaci na živém HA.

| Výsledek sestavení | Hodnota |
|---|---:|
| OTA soubor | 1 233 360 B |
| Factory soubor | 1 298 896 B |
| Obraz aplikace podle size | 1 232 956 B, 7,5 % aplikačního oddílu |
| Statická interní DIRAM | 106 874 / 576 464 B, 18,5 % |
| Statické sekce External RAM | 1 152 400 B |

Poslední řádek zahrnuje XIP sekce, není měřením dynamické spotřeby PSRAM.
Hash kontrola potvrdila nezměněné původní konfigurace základu, VGA, 720p,
D1 a D2. Dočasné secrets byly odstraněny. Do HA nebyl instalován žádný doplněk
ani skript a nic nebylo flashováno.

Vyřešené verze v `investigation/assist-message/dependencies.lock`:
esp_video 2.3.0, usb_host_uvc 2.5.2, esp_cam_sensor 2.3.0, esp_ipa 2.2.0~1,
esp_h264 1.3.0, esp_sccb_intf 1.0.0, cmake_utilities 0.5.3, mdns 1.12.0,
esp-audio-libs 3.2.1, micro-flac 0.2.0, IDF 5.5.5; lokální noise-c/libsodium `*`.

Matematická kontrola skutečných Q15 koeficientů: jednotkové DC zesílení,
symetrie, odchylka pod 0,1 dB v pásmu 0–5 kHz (krok 100 Hz) a potlačení
nad 8 kHz přes 40 dB (kontrolní mřížka po 50 Hz). Např. na 8 kHz −57,05 dB.
To ověřuje filtr, nikoli poslech ani časování celé komponenty na desce.
Opakovatelný test je `tests/check_mic_filter.py`, výsledky
`investigation/assist-message/filter-check.json`.

HA skript je připravený podle dokumentovaného rozhraní. Není ověřený živým
spuštěním v uživatelově HA; konkrétní satelit, STT/TTS a File entita se vybírají
až při nasazení. Kamera + HuskyLens + Assist, opakované spuštění/zastavení,
návrat hudby, zpoždění a kvalita přepisu zůstávají k testu na desce.

Očekávané logy: `48 -> 16 kHz microphone started (FIR low-pass)`,
`D3: Assist pipeline spustena`, `D3: prepis prijat; text vraci HA skriptu`,
`D3: Assist pipeline ukoncena`. Při tichu nebo nedostupném STT skript zobrazí
zprávu bez přepisu; podrobnost bude ve stopě skriptu a logu Assistu.
