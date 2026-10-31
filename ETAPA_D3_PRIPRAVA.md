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


# D3 — Prepared Assist Variant for Messaging

Firmware: `esp32p4-assist-message.yaml`. HA Script: `home_assistant/door_message_script.yaml`.

## What Has Changed

The new YAML inherits the 720p camera, Ethernet, HuskyLens, and media player. It does not alter the original YAML files or playback settings. It adds a microphone on GPIO11—configured with the same parameters as in D1—along with a local `mic_48_to_16` adapter and the standard `voice_assistant` component. The microphone gain is set to 24 dB, matching D1. It does not use the HTTP receiver (nor its token or address), does not require an add-on repository, and does not utilize the ESP32-C6.

The 48 kHz to 16 kHz conversion is handled on-board. Verified in a local instance of ESPHome 2026.9.0:
`voice_assistant/__init__.py:196` requires 16 kHz;
`voice_assistant.cpp:21` uses a fixed frequency of 16 kHz;
`microphone/microphone_source.h` does not explicitly perform frequency conversion.

## Files for ESPHome

The following belong in the same directory in ESPHome:
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

Only the original secrets, `esp_encryption_key` and `ota_password`, remain.
This variant does not use `voice_receiver_ip` or `voice_receiver_token` from experiment D2.
The new firmware has its own build directory.
```sh
esphome config esp32p4-assist-message.yaml
esphome compile esp32p4-assist-message.yaml
```

## Setup and First Text Message in HA


2. For the satellite, select an existing Czech Assist pipeline. It must have a functional STT (Speech-to-Text) engine, as well as a TTS (Text-to-Speech) engine for the voice prompt. If TTS is not configured, set it up first, or alternatively, modify the `question_media_id` parameter to use a custom pre-recorded prompt.
3. Go to **Settings → Automations & Scenes → Scripts → Create new script**, open the YAML editor, and paste the entire content of `home_assistant/door_message_script.yaml`. Note that this represents the content of a single script within the UI, not the entire `scripts.yaml` file.
4. Run the script, specifying the chosen door satellite and the media player associated with the same device. Leave the archive field blank for your first attempt. If the UI does not prompt you to fill in these fields when running the script, go to **Developer Tools → Actions**, select the newly saved script, and enter the required values ​​there.
5. The script will pause any music, play the prompt, and wait for a short response. Please pause briefly after speaking. A transcript, along with a timestamp, should appear in your HA notifications.

Using `ask_question` without defining `answers` results in a free-form transcription. In this mode, HA terminates the pipeline immediately after the STT process; the message is not interpreted as a home automation command. Neither the wake word nor continuous listening mode is active. This applies specifically to the provided script and does not necessarily extend to any other automations a user might add later. Source: [question action](https://www.home-assistant.io/actions/assist_satellite.ask_question/)
and [HA implementation](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/components/assist_satellite/entity.py).

## Setup and First Text Message in HA


A **Stop Message** button is available. Additionally, the firmware includes a safety limit of 45 seconds from the start of the pipeline. Speech may end sooner, depending on the VAD (Voice Activity Detection) in HA; it is not a fixed 45-second recorder. Do not play any other music or announcements on the same player while this is active. The script does not automatically resume previously playing music.

## Optional Persistent Text Storage

For initial testing, simple notifications are sufficient. To create an archive, set up a directory at `/config/vzkazy` and enable it within the existing `homeassistant` section of your HA configuration:
```yaml
homeassistant:
  allowlist_external_dirs:
    - /config/vzkazy
```
Merge with the existing configuration; do not overwrite other entries. After checking the configuration and restarting, add a notification entity for `/config/vzkazy/navstevy.jsonl` under **Devices & Services → Integrations → File**. If the integration offers its own timestamp, leave it disabled: the provided script includes the timestamp within the JSON data. Select this notification entity in the archive field when running the script.

Each successful message is appended as a JSON line. Newlines and quotation marks within the text are properly serialized; the content is never injected directly into a shell command. The data is not truncated to fit the state sensor limit. The file is not automatically rotated; you will need to manage its archiving and size during regular operation.
Source: [File](https://www.home-assistant.io/integrations/file/).

## Optional: Listening to the Original Voice Input

The provided file `home_assistant/assist_debug_recording.example.yaml`
configures diagnostic recording to `/media/assist_debug`. Merge this
into your Home Assistant configuration, verify the configuration, and restart Home Assistant.
After the next interaction, look for a WAV file under **Media → My Media → assist_debug**,
within a subdirectory corresponding to that specific session.

Note that this is a global diagnostic tool: it may record audio from other satellites,
does not automatically delete files, and is not directly linked to text-based notifications.
Once you have verified the audio quality, disable this feature and restart Home Assistant.
Accessing the actual file location and playing the recordings may require specific
permissions within your HA OS installation. While the official documentation
recommends using `/share/assist_pipeline`, this approach achieves the same
functionality using the media directory.


Zdroj: [diagnostické nahrávky Assist](https://www.home-assistant.io/voice_control/troubleshooting/).



