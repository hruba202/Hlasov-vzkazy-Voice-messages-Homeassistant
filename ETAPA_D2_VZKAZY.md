# D2 — desetisekundový vzkaz do Home Assistant OS

Nový YAML: `esp32p4-voice-message.yaml`. Původní konfigurace včetně D1 zůstávají
zachované. D2 dědí kameru 720p a základ s HuskyLens a media_player; mikrofon
používá stejné zapojení a parametry jako úspěšně spuštěný test D1.

## Co přibylo

- Lokální komponenta `components/voice_recorder`: přesně 480 000 vzorků
  (10 sekund mono 48 kHz, 16 bit) v bufferu **960 000 B PSRAM**.
- Po skončení snímání samostatná úloha odešle PCM přes HTTP do přijímače.
  Síťové čekání neprobíhá v hlavní smyčce ESPHome ani v úloze mikrofonu.
- Doplněk `addons/p4_voice_receiver` pro HA OS uloží WAV do médií.
- Tlačítka **Nahrat vzkaz 10 s**, **Zrusit nahravani vzkazu**; stavový senzor
  **Vzkaz stav**, příznak **Vzkaz probiha**, stav mikrofonu a hodnoty RMS/Peak.
- V klidu se nenahrává. Zrušení během snímání zahodí nahrávku. Po zahájení
  odesílání už tlačítko odeslání neruší a do logu se zapíše vysvětlení.
- Při neúplném příjmu vzorků se snímání po 15 sekundách ukončí bez uploadu.
  Další záznam se během snímání nebo odesílání odmítne.

Jde o první test záznamu, nikoli živý poslech nebo kompletní zvonkovou
automatizaci. Neobsahuje výzvy, automatické rozpoznání ticha ani notifikace.

## Instalace

1. Postupujte podle [návodu přijímače](addons/p4_voice_receiver/README.md).
   Není potřeba samostatný počítač pro běžný provoz ani změny Proxmoxu.
2. Do **vlastního stávajícího** ESPHome `secrets.yaml` přidejte dvě položky:

   ```yaml
   voice_receiver_ip: "IP_ADRESA_HA_OS"
   voice_receiver_token: "VLASTNI_NAHODNY_KLIC_64_HEX_ZNAKU"
   ```

   Zástupné hodnoty nahraďte; první musí být skutečná IPv4 a druhá 64 malých
   hexadecimálních znaků shodných s `token` v doplňku. Stávající
   `esp_encryption_key` a `ota_password` zachovejte. Žádné heslo není v YAML
   natvrdo. Přenosový klíč neposílejte do reportu ani do Gitu.
3. Vedle nového YAML musí být původní tři základní/kamerové YAML soubory
   a celý adresář `components`. D1 YAML není závislostí D2.
4. Ověřte a sestavte s vlastními secrets:

   ```sh
   esphome config esp32p4-voice-message.yaml
   esphome compile esp32p4-voice-message.yaml
   ```



Přijímač má zapsat `Saved vzkaz_...wav: mono 48000 Hz, 16 bit, 10 seconds`.
Při problému: 401 = jiný klíč; 400/415 = délka nebo formát; 503 = probíhá
jiný upload; 507 = limit souborů nebo málo místa. Záporný výsledek na ESP32
znamená chybu přenosu, například špatnou IP, nedostupný port či timeout.
V klidu je varování `sound_level`, že mikrofon neběží, očekávané.


Vzniklo ve spolupráci s ChatGPT / Codex od OpenAI, stejně jako zbytek projektu.

# D2 — A 10-second message for Home Assistant OS

New YAML file: `esp32p4-voice-message.yaml`. The original configuration, including D1, remains intact. D2 inherits the 720p camera setup, the HuskyLens integration, and the `media_player` component; the microphone uses the same wiring and parameters as the successfully tested D1 configuration.

## New Features

- A local component, `components/voice_recorder`, captures exactly 480,000 samples (10 seconds of mono audio at 48 kHz, 16-bit) into a **960,000-byte PSRAM buffer**.
- Once recording is complete, a separate task transmits the PCM data via HTTP to a receiver. Network-related wait times do not block the main ESPHome loop or the microphone task.
- An add-on, `addons/p4_voice_receiver` for HA OS, saves the audio as a WAV file in the media directory.
- Controls include **Record 10s Message** and **Cancel Message Recording**. Status monitoring features include a **Message Status** sensor, a **Recording in Progress** flag, microphone status, and RMS/Peak values.
- No recording occurs while the system is idle. Canceling during the recording phase discards the captured audio. Once the transmission phase has begun, the cancel action is disabled, and an explanatory note is written to the log.
- If the sample capture is incomplete, the recording process terminates after 15 seconds without uploading any data. Any attempt to start a new recording while a capture or transmission is already in progress will be rejected.

This is an initial test of the recording functionality—it does not include live audio monitoring or a complete doorbell automation system. It does not include wake words, automatic silence detection, or notifications.

## Installation

1. Follow the [receiver instructions](addons/p4_voice_receiver/README.md).
   No separate computer is required for standard operation, nor are any changes to Proxmox necessary.
2. Add two entries to your **existing** ESPHome `secrets.yaml` file:

   ```yaml
   voice_receiver_ip: "HA_OS_IP_ADDRESS"
   voice_receiver_token: "YOUR_OWN_RANDOM_64_CHARACTER_HEX_KEY"
   ```

   Replace the placeholder values; the first must be a valid IPv4 address, and the second must consist of 64 lowercase hexadecimal characters matching the `token` defined in the add-on. Keep your existing `esp_encryption_key` and `ota_password`. No passwords are hardcoded in the YAML. Do not include the transmission key in any reports or Git repositories.
3. In addition to the new YAML file, the original three base/camera YAML files
   and the entire `components` directory must be present. The D1 YAML is not a dependency of D2.
4. Verify and compile using your own secrets:

   ```sh
   esphome config esp32p4-voice-message.yaml
   esphome compile esp32p4-voice-message.yaml
   ```



The receiver should log: `Saved vzkaz_...wav: mono 48000 Hz, 16 bit, 10 seconds`.
In case of issues: 401 = incorrect key; 400/415 = invalid length or format; 503 = another upload is already in progress; 507 = file limit reached or insufficient storage space. A negative result on the ESP32 indicates a transmission error, such as an incorrect IP address, an unreachable port, or a timeout.
A `sound_level` warning during idle periods—indicating that the microphone is not active—is expected.


Created in collaboration with OpenAI's ChatGPT / Codex, as was the rest of the project.

   


