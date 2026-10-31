# Hlasové vzkazy / Voice messages for Home Assistant

**CZ:** Experimentální projekt pro návštěvy u dveří: když nikdo není doma,
návštěva nechá hlasový vzkaz, který se uloží v Home Assistantu. Součástí je
vlastní integrace HA **Voice Inbox** (univerzální příjem zvuku z ESP32 a z
prohlížeče) a firmware ESPHome pro desku **Waveshare ESP32-P4-WIFI6-POE-ETH**
(USB kamera, mikrofon/reproduktor ES8311, interkom, HuskyLens).



## Stručný souhrn / Short summary

| Etapa | Obsah | Stav |
|---|---|---|
| D1 | Test mikrofonu (30 s) | funguje |
| D2 | Přijímač jako doplněk HA OS | slepá ulička (doplňky = Docker kontejnery, ruční kopírování nedává smysl) |
| D3 | Assist / textový vzkaz | slepá ulička pro interkom (konflikt o vlastnictví audia) |
| D4 | Interkom P4 ↔ zařízení s displejem, obraz na kartě | testováno v obou směrech; občasné drobné sekání |
| **Etapa 1** | **HA integrace Voice Inbox 0.3.1** | panel v HA funguje (potvrzeno uživatelem) |
| D5 | 10 s vzkaz z P4 do Voice Inboxu | firmware připraven; ověření na desce viz `ETAPA_D5_VZKAZ_P4.md` |
| D6 | Vlastní zvonek: HA integrace `p4_doorbell` 0.1.1 (posouzení + implementace) | testy a návod v `etapa_d6_zvonek/`; chování na reálném HA neověřeno touto revizí |
| D7 | Zvonek + hlasové vzkazy: `p4_doorbell` 0.2.0 (přidává `mailbox.py`) | viz `etapa_d7_vzkaz/D7-NAVOD.md`; chování na reálném HA neověřeno touto revizí |
| D8 | Fyzické tlačítko zvonku (GPIO2) + `p4_doorbell` 0.3.0 (`visitor.py`) | viz `etapa_d8_tlacitko/D8-NAVOD.md` a `OVERENI.md`; firmware `esp32p4-doorbell-button.yaml`; chování na reálném HA neověřeno touto revizí |


## Voice Inbox (HA integrace)

- Příjem z ESP po LAN: `POST /api/voice_inbox/upload` (hlavičky `X-Voice-Source`,
  `X-Voice-Key`, `X-Audio-Rate/Bits/Channels`); odmítá Nabu Casa a `X-Forwarded-*`,
  omezení 5 chyb / IP / 60 s.
- Panel pouze pro správce: `/voice-inbox` (nahrávání z mikrofonu prohlížeče,
  přehrávání, výběr zdroje).
- Úložiště `/media/vzkazy/<zdroj>/`, kvóta 100 WAV bez automatického mazání,
  upozornění při 80 %, entity a událost `voice_inbox_saved`.
- Instalace: rozbalte `packages/voice-inbox-stage1-0.3.1.zip`, složku
  `custom_components/voice_inbox` zkopírujte do `/config/custom_components/`
  a restartujte **celý** HA. Podrobnosti: `etapa1_voice_inbox/README.md`.

## Struktura repozitáře

| Cesta | Obsah |
|---|---|
| `etapa1_voice_inbox/` | integrace Voice Inbox, testy, nástroje, `VALIDATION.md` |
| `esp32p4-*.yaml` | konfigurace ESPHome (kamera, mikrofon, interkom, vzkazy) |
| `components/` | vlastní komponenty ESPHome (`p4_voice_inbox`, `huskylens_bridge`, `mic_48_to_16`, …) |
| `etapa_d6_zvonek/`, `etapa_d7_vzkaz/`, `etapa_d8_tlacitko/` | HA integrace `p4_doorbell` (zvonek; od D7 i vzkazy), testy, návody |
| `addons/p4_voice_receiver/` | původní přijímač D2 (zachováno pro historii) |
| `home_assistant/` | ukázkové skripty a pomocné konfigurace |
| `packages/` | hotové ZIP balíčky (viz níže) |
| `ETAPA*.md`, `JEDNA_DESKA_POSOUZENI.md` | zápisy a posouzení jednotlivých etap |
| `README-P4.md` | původní README firmwaru P4 |

## Balíčky (`packages/`)

| Soubor | Účel |
|---|---|
| `voice-inbox-stage1-0.3.1.zip` | HA integrace Voice Inbox (aktuální) |
| `D5-intercom-vzkazy-package.zip` | firmware: interkom + 10 s vzkaz z P4 |
| `D4-intercom-package.zip` | firmware: interkom |
| `D3-assist-package.zip` | firmware: Assist (slepá ulička) |
| `p4_voice_receiver-0.1.0.zip` | doplněk D2 (slepá ulička) |
| `D6-zvonek-0.1.1.zip` | HA integrace zvonku (D6) |
| `D7-zvonek-vzkazy-0.2.0.zip` | HA integrace zvonku + vzkazy (D7) |
| `D8-zvonek-tlacitko-0.3.0.zip` | zvonek + fyzické tlačítko + firmware YAML (D8, aktuální) |

Balíčky byly sestaveny ze zdrojů v repozitáři; obsah každé položky odpovídá
originálním ZIPům (kontrola SHA-256 po položkách).

## Ověřený stav a upozornění

- ESPHome 2026.10.0, ESP-IDF 5.5.5, HA Core 2026.10.3. Firmware **nenahrávejte**
  bez vlastní kompilace a kontroly; `secrets.yaml` do repozitáře nepatří
  (vzor: `voice-inbox-secrets.example.yaml`).
- Testy integrace používají náhrady API Home Assistantu; celý start v reálném HA
  je ověřen jen ručně na jedné instalaci.
- Dokumentace a testy obsahují ukázkové privátní LAN adresy (192.168.x.x)
  a ukázkový název zdroje `annahp`; nejde o tajné údaje.
- Nezahrnuto: logy z validace D8 (`*.log`), balíček D6 0.1.0 (nahrazen 0.1.1), `investigation/` (cizí repozitáře a logy), virtuální
  prostředí a sestavovací artefakty.
- Nejde o oficiální integraci Home Assistantu.

Kód vznikal ve spolupráci s AI (ChatGPT/Codex a Claude)

**EN:** Experimental project for door visitors: when nobody is home, a visitor
can leave a voice message that is stored in Home Assistant. It contains a custom
HA integration, **Voice Inbox** (a generic receiver for audio from ESP32 devices
and from the browser), and ESPHome firmware for the Waveshare ESP32-P4 board
(USB camera, ES8311 audio, two-way intercom, HuskyLens).
## Brief Summary

| Stage | Content | Status |
|---|---|---|
| D1 | Microphone test (30 s) | Working |
| D2 | Receiver as an HA OS Add-on | Dead end (Add-ons = Docker containers; manual copying makes no sense) |
| D3 | Assist / Text message | Dead end for intercom use (audio ownership conflict) |
| D4 | P4 Intercom ↔ Device with display, video feed to card | Tested in both directions; occasional minor stuttering |
| **Stage 1** | **HA Integration: Voice Inbox 0.3.1** | HA panel is functional (confirmed by user) |
| D5 | 10-second message from P4 to Voice Inbox | Firmware ready; verification details in `ETAPA_D5_VZKAZ_P4.md` |
| D6 | Custom Doorbell: HA integration `p4_doorbell` 0.1.1 (assessment + implementation) | Tests and instructions in `etapa_d6_zvonek/`; behavior on an actual HA instance not verified in this revision |
| D7 | Doorbell + Voice Messages: `p4_doorbell` 0.2.0 (adds `mailbox.py`) | See `etapa_d7_vzkaz/D7-NAVOD.md`; behavior on an actual HA instance not verified in this revision |
| D8 | Physical doorbell button (GPIO2) + `p4_doorbell` 0.3.0 (`visitor.py`) | see `etapa_d8_tlacitko/D8-NAVOD.md` and `OVERENI.md`; firmware `esp32p4-doorbell-button.yaml`; behavior on a live HA instance has not been verified in this revision |

## Voice Inbox (HA Integration)

- Reception from ESP via LAN: `POST /api/voice_inbox/upload` (headers: `X-Voice-Source`,
  `X-Voice-Key`, `X-Audio-Rate/Bits/Channels`); rejects Nabu Casa and `X-Forwarded-*`
  requests; rate limit: 5 errors per IP per 60 seconds.
- Admin-only panel: `/voice-inbox` (recording from browser microphone,
  playback, source selection).
- Storage: `/media/vzkazy/<source>/`; quota of 100 WAV files with no automatic deletion;
  notification at 80% capacity; includes entities and a `voice_inbox_saved` event.
- Installation: Unzip `packages/voice-inbox-stage1-0.3.1.zip`, copy the
  `custom_components/voice_inbox` folder to `/config/custom_components/`,
  and restart the **entire** HA instance. Details: `etapa1_voice_inbox/README.md`.
## Struktura repozitáře

## Repository Structure

| Path | Content |
|---|---|
| `etapa1_voice_inbox/` | Voice Inbox integration, tests, tools, `VALIDATION.md` |
| `esp32p4-*.yaml` | ESPHome configurations (camera, microphone, intercom, messages) |
| `components/` | Custom ESPHome components (`p4_voice_inbox`, `huskylens_bridge`, `mic_48_to_16`, …) |
| `etapa_d6_zvonek/`, `etapa_d7_vzkaz/`, `etapa_d8_tlacitko/` | HA integration `p4_doorbell` (doorbell; includes messaging from D7 onwards), tests, guides |
| `addons/p4_voice_receiver/` | Original D2 receiver (retained for historical reference) |
| `home_assistant/` | Example scripts and auxiliary configurations |
| `packages/` | Ready-to-use ZIP packages (see below) |
| `ETAPA*.md`, `JEDNA_DESKA_POSOUZENI.md` | Records and assessments of individual stages |
| `README-P4.md` | Original README for the P4 firmware |

## Packages (`packages/`)

| File | Purpose |
|---|---|
| `voice-inbox-stage1-0.3.1.zip` | Voice Inbox HA integration (current) |
| `D5-intercom-vzkazy-package.zip` | Firmware: Intercom + 10s message from P4 |
| `D4-intercom-package.zip` | Firmware: Intercom |
| `D3-assist-package.zip` | Firmware: Assist (deprecated/dead end) |
| `p4_voice_receiver-0.1.0.zip` | D2 add-on (deprecated/dead end) |
| `D6-zvonek-0.1.1.zip` | Doorbell HA integration (D6) |
| `D7-zvonek-vzkazy-0.2.0.zip` | Doorbell HA integration + messages (D7) |
| `D8-zvonek-tlacitko-0.3.0.zip` | Doorbell + physical button + firmware YAML (D8, current) |

The packages were built from the source code in the repository; the contents of each item correspond to the
original ZIP files (verified via SHA-256 checksums for each item).

## Verified Status and Notes

- ESPHome 2026.10.0, ESP-IDF 5.5.5, HA Core 2026.10.3. Do **not** flash the firmware
  without compiling it yourself and reviewing the code; `secrets.yaml` should not be included in the repository
  (see the template: `voice-inbox-secrets.example.yaml`).
- Integration tests use mocks for the Home Assistant API; the full startup process in a live Home Assistant environment
  has only been manually verified on a single installation.
- The documentation and tests contain example private LAN addresses (192.168.x.x)
  and an example source name, `annahp`; these are not sensitive data.
- Excluded: D8 validation logs (`*.log`), D6 package version 0.1.0 (replaced by 0.1.1), the `investigation/` directory (external repositories and logs), virtual
  environments, and build artifacts.
- This is not an official Home Assistant integration.

The code was developed in collaboration with AI (ChatGPT/Codex and Claude).
