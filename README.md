# Hlasové vzkazy / Voice messages for Home Assistant

**CZ:** Experimentální projekt pro návštěvy u dveří: když nikdo není doma,
návštěva nechá hlasový vzkaz, který se uloží v Home Assistantu. Součástí je
vlastní integrace HA **Voice Inbox** (univerzální příjem zvuku z ESP32 a z
prohlížeče) a firmware ESPHome pro desku **Waveshare ESP32-P4-WIFI6-POE-ETH**
(USB kamera, mikrofon/reproduktor ES8311, interkom, HuskyLens).

**EN:** Experimental project for door visitors: when nobody is home, a visitor
can leave a voice message that is stored in Home Assistant. It contains a custom
HA integration, **Voice Inbox** (a generic receiver for audio from ESP32 devices
and from the browser), and ESPHome firmware for the Waveshare ESP32-P4 board
(USB camera, ES8311 audio, two-way intercom, HuskyLens).

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

Pozdější etapa (`etapa_d8_tlacitko`) zatím **není zahrnuta**.

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
| `etapa_d6_zvonek/`, `etapa_d7_vzkaz/` | HA integrace `p4_doorbell` (zvonek; od D7 i vzkazy), testy, návody |
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
| `D7-zvonek-vzkazy-0.2.0.zip` | HA integrace zvonku + vzkazy (D7, aktuální) |

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
- Nezahrnuto: etapa D8, balíček D6 0.1.0 (nahrazen 0.1.1), `investigation/` (cizí repozitáře a logy), virtuální
  prostředí a sestavovací artefakty.
- Nejde o oficiální integraci Home Assistantu.

Kód vznikal ve spolupráci s AI (ChatGPT/Codex a Claude), revize a testy na
hardwaru provedl autor.
