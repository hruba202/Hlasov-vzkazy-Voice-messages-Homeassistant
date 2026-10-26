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

## První pokus — jen tlačítky v HA

1. Otevři **Nastavení → Zařízení a služby → ESPHome → ESP32-P4**.
2. Ukonči případný hovor a vypni **Interkom ztlumit mikrofon**.
3. Stiskni **Vzkaz nahrat 10 s**. Přehrávání hudby se zastaví; nahrávání
   začne až po uvolnění reproduktoru, nejdéle po čekání 3 sekundy.
4. Jakmile **Vzkaz stav** ukáže **Nahravam, nejvyse 10 s**, mluv do mikrofonu P4.
   Senzor **Vzkaz nahrava** bude zapnutý.
5. Po 10 sekundách zvuku se vzkaz odešle automaticky. Můžeš stisknout
   **Vzkaz zastavit a ulozit** dříve (minimum 0,5 sekundy), nebo **Vzkaz zrusit**.
6. Počkej na **Odesilam do HA → Ulozeno v HA**.
7. V levém menu otevři **Hlasové vzkazy**, vyber stejný zdroj a stiskni
   **Obnovit a načíst vzkaz**. Přehrávačem poslechni skutečný soubor uložený v HA.
   Tlačítko Nahrát na této stránce nadále používá mikrofon PC/telefonu;
   pro P4 používej nové tlačítko u zařízení ESP32-P4.

Zopakuj při běžícím obrazu kamery. Potom ověř obyčejný hovor oběma směry
a přehrávání hudby, aby se potvrdilo vrácení mikrofonu a reproduktoru do provozu.

## Chování a hranice tohoto testu

- Záznam je **48 kHz / 16 bit / mono**, bez změny nebo převzorkování mikrofonu.
  HA vytvoří WAV v mediálním adresáři `vzkazy/<zdroj>/` a vyvolá dosavadní událost.
- Vyhrazený buffer v PSRAM má **960 000 B** (asi 0,916 MiB) pro nejvýše 10 sekund.
  Alokuje se jednou při startu. Uploader má navíc 8192 B zásobníku a režii HTTP.
  Síťový přenos běží v samostatné úloze, ne v audio callbacku ani hlavní smyčce.
- Audio hardware stále řídí **esp_audio_stack**. Rekordér se připojuje ke
  stávajícímu `door_mic` přes callback a vyvážené `start()/stop()`.
  Tato připnutá verze mikrofonu počítá posluchače; vlastní I2S ani kodek nepřidáváme.
- Během vyzvánění či hovoru se nahrávání nespustí. Pokud se volání rozběhne
  při záznamu, záznam se zahodí a uvolní svůj mikrofonní požadavek.
  Již zahájené odesílání hotového souboru doběhne i během nového hovoru;
  mikrofon už v té chvíli rekordér nepoužívá. Souběh může krátce zatížit síť/CPU.
- Ztlumený mikrofon se automaticky neodtlumuje. Ztlumení při záznamu ho zruší.
- Hudba se po nahrávání automaticky neobnovuje. Nespouštěj ji během záznamu,
  jinak se zachytí také zvuk reproduktoru.
- Zrušení funguje před odesíláním. Již odeslaný vzkaz se automaticky nemaže.
  Síťová chyba záznam neukládá trvale v P4, nezachovává ho po restartu a neopakuje upload.
  Při ztraceném potvrzení nejprve obnov schránku, soubor už může existovat.
- Záznamy hovorů, výzva „nechte vzkaz“, automatické spuštění po nezvednutí,
  upozornění telefonu a přepis do textu nejsou součástí tohoto kroku.

## Spojení a řešení chyb

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

## Ověření

**25. 10. 2026: `esphome config` i plná kompilace úspěšné** na ESPHome
2026.10.0 / ESP-IDF 5.5.5. Všechny vyřešené verze závislostí odpovídají
dosavadnímu sestavení D4. SHA256 potvrzuje nezměněné oba D4 YAML i původní D2 rekordér.

| Položka | Výsledek |
|---|---:|
| OTA binárka | 1 455 104 B |
| Factory binárka | 1 520 640 B |
| Statická interní RAM | 109 784 / 576 464 B (19,0 %) |
| Obraz podle linkeru | 1 454 714 B (8,8 % oddílu) |
| Nový buffer v PSRAM za běhu | 960 000 B |

Údaj statické RAM nezahrnuje živou haldu, síťové buffery ani úlohy. Živou
spotřebu PSRAM a kvalitu zvuku musí potvrdit deska. Kompilace obsahuje i známá
upozornění kompatibilní kamerové komponenty (`ESPHOME_LOG_TAG`); sestavení nezastavila.
Dočasné testovací secrets byly odstraněny. ZIP neobsahuje binárky ani secrets.

Výsledky validace a plné kompilace jsou v `investigation/d5/`.
Kontrolní sestavení není potvrzením skutečného příjmu na konkrétní LAN:
prohlížeč používal přihlášení HA, P4 musí zvlášť projít pravidlem LAN a klíčem zdroje.
Příjem, srozumitelnost a souběh s kamerou/hovorem se ověří až tímto pokusem na desce.

Podklad pro sdílení mikrofonu: připnutý soubor
`esp_audio_stack/microphone/esp_audio_stack_microphone.cpp`, metody `start`,
`release_listener_`, `stop`, `on_audio_data_`:
https://github.com/n-IA-hane/esphome-audio-stack/blob/0482d741a938378ef948e3b8f3dd31536f9f2cc9/esphome/components/esp_audio_stack/microphone/esp_audio_stack_microphone.cpp

Připraveno s pomocí ChatGPT / Codex od OpenAI. Původní audio a VoIP komponenty
pocházejí z projektů n-IA-hane.
