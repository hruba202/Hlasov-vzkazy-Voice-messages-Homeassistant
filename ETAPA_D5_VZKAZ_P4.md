# D5 — ruční hlasový vzkaz z P4 do existujícího Voice Inboxu

Tato varianta rozšiřuje fungující D4 intercom. Hovory, kamera 1280×720,
HuskyLens, Ethernet, ES8311, piny a připnuté revize zůstávají stejné.
Původní `esp32p4-intercom.yaml` ani jeho základ se neupravují.

## Co použít

Hlavní konfigurace je **esp32p4-intercom-vzkazy.yaml**. Vedle ní musí být
dosavadní `esp32p4-intercom.yaml`, `esp32p4-intercom-base.yaml` a složka
`components`. Nově přibyla `components/p4_voice_inbox/` (tři soubory).
ZIP obsahuje i kopie potřebných původních souborů pro samostatné sestavení.
Pokud sis mezitím D4 lokálně upravil, jeho soubory nepřepisuj: přidej jen nový
hlavní YAML a novou komponentu a zkompiluj proti svému základu.

1. Do svého **ESPHome secrets.yaml** doplň tři položky podle
   `voice-inbox-secrets.example.yaml`. Původní API klíč a OTA heslo zachovej.
   - `voice_inbox_ha_ip`: lokální IP Home Assistanta; zde předpoklad 192.168.0.36.
   - `voice_inbox_source`: přesný zdroj v integraci Voice Inbox; na tvém obrázku `annahp`.
   - `voice_inbox_key`: jeho původní 64znakový uploadovací klíč, nikoli HA token.
   Klíč nikam do chatu neposílej. Pro jiný port změň `receiver_port` v novém YAML.
2. V nastavení zdroje Voice Inbox musí povolená síť zahrnovat **IP P4**, nejen
   počítače. Pro dosavadní síť lze použít `192.168.0.0/24`, případně přesnou
   aktuální IP desky s `/32`. Starší log uváděl P4 192.168.0.19; ověř aktuální
   adresu, nenastavujeme ji napevno. Na `/24` musí být adresa sítě `.0`, nikoli `.87`.
3. Zkompiluj **esp32p4-intercom-vzkazy.yaml** v ESPHome 2026.10.0 se svými
   přístupovými údaji. Zařízení má stejné jméno a API jako stávající P4.
   Není potřeba přidávat nové zařízení do HA.
4. Firmware nahraj sám až po úspěšné plné kompilaci. Agent nic neflashoval.
   Zdejší kontrolní binárky používají náhodné testovací údaje a nejsou pro nasazení.

Pokud původní uploadovací klíč neznáš, nejde ho z HA přečíst zpět: integrace
ukládá jen otisk. Založ samostatný zdroj například `dvere` s vlastním novým
klíčem a povolenou sítí P4, případně uprav konfiguraci zdroje podporovaným
způsobem v další etapě. Existující vzkazy kvůli testu nemaž.

P4 odesílá přímo do lokálního HA na `http://<IP>:8123/api/voice_inbox/upload`.
Hlavičky jsou `X-Voice-Source`, `X-Voice-Key`, `X-Audio-Rate: 48000`,
`X-Audio-Bits: 16`, `X-Audio-Channels: 1`, typ `application/octet-stream`.
Nejde o endpoint stránky prohlížeče ani původní D2 `/recordings`.
Použití HTTPS v prohlížeči zůstává nezávislé na tomto přenosu.

Tato první varianta používá přímé HTTP v důvěryhodné LAN, ne Nabu Casa URL,
proxy ani přesměrování. Klíč i audio jsou v tomto úseku přenášeny nešifrovaně.
Nevystavovat endpoint přes port forwarding; ochrana LAN v integraci zůstává zapnutá.

Očekávaný log:

```text
[p4_voice_inbox]: D5: buffer 960000 B in PSRAM, mono 48000 Hz / 16 bit, max 10 s
[p4_voice_inbox]: D5: Nahravam, nejvyse 10 s
[p4_voice_inbox]: D5: Odesilam do HA
[p4_voice_inbox]: D5: sending 960000 PCM bytes (10.0 s)
[p4_voice_inbox]: D5: upload HTTP result 201 (negative = transport error)
[p4_voice_inbox]: D5: Ulozeno v HA
```

- **401:** nesouhlasí klíč/zdroj, nebo LAN pravidlo nepovoluje P4.
- **503:** dočasná nedostupnost, souběžný upload, nebo blokace chybných klíčů.
  Po 5 chybných klíčích je IP blokovaná i se správným klíčem; vyčkej 60 sekund.
- **507:** dosažená kvóta nebo nedostatek místa. Nic se samo nemaže.
- **400/413/415:** odmítnutý požadavek, limit velikosti/délky nebo audio formát.
- **Záporný výsledek:** spojení či odpověď selhaly. Nejdřív ověř obsah schránky.
- **Mikrofon nedodal zvuk včas:** do 15 s nepřišel úplný 10s záznam;
  neúplný záznam se automaticky neodeslal. Zkontroluj log Audio Stacku.


Podklad pro sdílení mikrofonu: připnutý soubor
`esp_audio_stack/microphone/esp_audio_stack_microphone.cpp`, metody `start`,
`release_listener_`, `stop`, `on_audio_data_`:
https://github.com/n-IA-hane/esphome-audio-stack/blob/0482d741a938378ef948e3b8f3dd31536f9f2cc9/esphome/components/esp_audio_stack/microphone/esp_audio_stack_microphone.cpp

Připraveno s pomocí ChatGPT / Codex od OpenAI. Původní audio a VoIP komponenty
pocházejí z projektů n-IA-hane.



# D5 — Manual voice message from P4 to an existing Voice Inbox

This variant extends the functional D4 intercom. The calling features, 1280×720 camera,
HuskyLens, Ethernet, ES8311, pin assignments, and existing revisions remain unchanged.
The original `esp32p4-intercom.yaml` and its base configuration are not modified.

## What to use

The main configuration file is **esp32p4-intercom-vzkazy.yaml**. It requires the
existing `esp32p4-intercom.yaml`, `esp32p4-intercom-base.yaml`, and the `components`
directory to be present. A new directory, `components/p4_voice_inbox/` (containing three files),
has been added. The ZIP archive also includes copies of the necessary original files
to allow for an independent build. If you have modified your local D4 setup,
do not overwrite your existing files; simply add the new main YAML file and the
new component, then compile using your current base configuration.

1. Add three entries to your **ESPHome secrets.yaml** file, following the
   `voice-inbox-secrets.example.yaml` template. Keep your existing API key and OTA password.
   - `voice_inbox_ha_ip`: The local IP address of your Home Assistant instance (assumed here to be 192.168.0.36).
   - `voice_inbox_source`: The specific source identifier within the Voice Inbox integration; based on your image, this is `annahp`.
   - `voice_inbox_key`: The original 64-character upload key (not the Home Assistant token).
   Do not share this key in any chat. If you need to use a different port, change the `receiver_port` setting in the new YAML file. 2. In the Voice Inbox source settings, the allowed network must include the **P4 IP**, not just
   computers. For the existing network, you can use `192.168.0.0/24`, or alternatively, the specific
   current IP of the board with a `/32` suffix. An older log indicated the P4 address as 192.168.0.19;
   please verify the current address, as it is not set to a static value. Note that for a `/24` range,
   the network address must end in `.0`, not `.87`.
3. Compile **esp32p4-intercom-vzkazy.yaml** in ESPHome 2026.10.0, including your
   credentials. The device shares the same name and API as the existing P4.
   There is no need to add a new device to HA.
4. Flash the firmware yourself only after a successful, complete compilation. The agent did not flash anything.
   The binary files provided here use dummy test data and are not intended for deployment.

If you do not know the original upload key, it cannot be retrieved from HA; the integration stores only a hash. Create a separate source—for example, named `dvere`—with a new key and the P4 network enabled; alternatively, you can modify the source configuration in a supported manner at a later stage. Do not delete existing messages used for testing.
## Spojení a řešení chyb

P4 sends data directly to the local HA instance at `http://<IP>:8123/api/voice_inbox/upload`.
The headers used are `X-Voice-Source`, `X-Voice-Key`, `X-Audio-Rate: 48000`,
`X-Audio-Bits: 16`, and `X-Audio-Channels: 1`, with the content type set to `application/octet-stream`.
This is not the same as the browser-based endpoint or the original D2 `/recordings` endpoint.
The use of HTTPS in the browser is independent of this data transmission.

This initial approach uses plain HTTP within a trusted LAN; it does not involve Nabu Casa URLs,
proxies, or port forwarding. Both the key and the audio data are transmitted unencrypted during this stage.
Do not expose this endpoint via port forwarding; the LAN protection feature within the integration remains active.

Expected log output:

```text
[p4_voice_inbox]: D5: buffer 960000 B in PSRAM, mono 48000 Hz / 16 bit, max 10 s
[p4_voice_inbox]: D5: Recording, max 10 s
[p4_voice_inbox]: D5: Sending to HA
[p4_voice_inbox]: D5: sending 960000 PCM bytes (10.0 s)
[p4_voice_inbox]: D5: upload HTTP result 201 (negative = transport error)
[p4_voice_inbox]: D5: Saved in HA
```

- **401:** The key/source does not match, or the LAN policy does not permit access for P4. - **503:** Temporary unavailability, concurrent upload, or blocking due to incorrect keys.
  After 5 incorrect key attempts, the IP address is blocked—even if the correct key is provided; please wait 60 seconds.
- **507:** Quota reached or insufficient space. No data is deleted automatically.
- **400/413/415:** Request rejected; size/length limit exceeded, or unsupported audio format.
- **Negative result:** Connection or response failure. First, verify the contents of the buffer.
- **Microphone failed to provide audio in time:** A complete 10-second recording was not received within 15 seconds;
  the incomplete recording was not sent automatically. Check the Audio Stack log.


Reference for microphone sharing: see the attached file
`esp_audio_stack/microphone/esp_audio_stack_microphone.cpp`, specifically the methods `start`,
`release_listener_`, `stop`, and `on_audio_data_`:
https://github.com/n-IA-hane/esphome-audio-stack/blob/0482d741a938378ef948e3b8f3dd31536f9f2cc9/esphome/components/esp_audio_stack/microphone/esp_audio_stack_microphone.cpp

Prepared with the assistance of OpenAI's ChatGPT / Codex. The original audio and VoIP components
originate from projects by n-IA-hane.
