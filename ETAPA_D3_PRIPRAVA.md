# D3 — připravená varianta Assist pro vzkazy


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

## Nastavení a první textový vzkaz v HA


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



