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

5. Až po úspěšné plné kompilaci lze firmware nasadit. Agent nic neflashuje.
   Lokální ověřovací binárka používá dočasné údaje a není určena k nahrání.

## První test

1. Ověřte běh přijímacího doplňku. Na desce zastavte hudbu; během snímání
   nespouštějte hlášení. Příkazy přehrávače nejsou automaticky blokované.
2. Stiskněte **Nahrat vzkaz 10 s**. Řekněte krátkou větu a chvíli mlčte.
3. Stav má projít `Nahravam 10 s` → `Odesilam do HA` → `Ulozeno v HA`.
   Poslední stav znamená HTTP 201 od přijímače, nikoli pouze ukončení snímání.
4. V **Média → Moje média → vzkazy** otevřete nový WAV. Při potřebe obnovte
   seznam. Nahrávka má 10 sekund a 960 044 bajtů; název používá čas UTC.
5. Zkontrolujte srozumitelnost, výpadky, hlasitost, obraz kamery a HuskyLens.
   Poté ověřte, že lze znovu přehrávat hudbu. Vyzkoušejte i předčasné zrušení
   snímání — po něm se nový soubor nemá objevit.

Očekávaný log ESP32:

```text
D2: Nahravam 10 s
D2: Odesilam do HA
D2: Ulozeno v HA
```

Přijímač má zapsat `Saved vzkaz_...wav: mono 48000 Hz, 16 bit, 10 seconds`.
Při problému: 401 = jiný klíč; 400/415 = délka nebo formát; 503 = probíhá
jiný upload; 507 = limit souborů nebo málo místa. Záporný výsledek na ESP32
znamená chybu přenosu, například špatnou IP, nedostupný port či timeout.
V klidu je varování `sound_level`, že mikrofon neběží, očekávané.

## Ověřené a neověřené

Pět síťových testů Python přijímače prošlo: zachování PCM ve WAV a správná
délka/formát; odmítnutí nesprávného klíče/délky/typu; úklid přerušeného
uploadu; limit počtu nahrávek bez mazání; odmítnutí souběžného zápisu.
Testovací provoz byl pouze na loopback adrese tohoto PC, nikoli na HA.

Validace YAML, generování C++ a plná kompilace prošly (ESPHome 2026.9.0,
ESP-IDF 5.5.5). OTA: 1 216 928 B; factory: 1 282 464 B. Statická interní
DIRAM: 106 410 / 576 464 B (18,5 %); statické sekce External RAM: 1 135 968 B.
To není dynamické maximum PSRAM. Lock a log jsou v `investigation/voice-message`.
Hash kontrola potvrdila nezměněné původní čtyři YAML soubory včetně D1.
Dočasné secrets pro kompilaci byly odstraněny, vzniklé binárky nenahrávat.
Docker zde není dostupný: sestavení kontejneru, instalace v HA OS, skutečný
přenos ESP32 → HA a poslech mikrofonu zůstávají k praktickému ověření.
Úspěšný test D1 potvrzuje vzorky a souběh kamery, nikoli srozumitelnost řeči.

Dynamická spotřeba: trvale vyhrazených 960 kB PSRAM pro záznam, k tomu
buffery mikrofonu/statistik, interní stack upload úlohy 8 KiB a síťové alokace.
Celkové maximum RAM/PSRAM a vliv na fps je třeba změřit na desce.
Přenos je lokální HTTP s klíčem, bez TLS; viz omezení v návodu přijímače.

Vzniklo ve spolupráci s ChatGPT / Codex od OpenAI, stejně jako zbytek projektu.

Aktuální doporučení po změně požadavku: viz [D3 — Assist, text a hlas](ETAPA_D3_ASSIST_POSOUZENI.md).
D2 je zachovaná experimentální alternativa, nikoli nutná instalace pro D3.
