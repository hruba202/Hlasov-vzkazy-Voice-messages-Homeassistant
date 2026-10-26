# Etapa D: mikrofon na desce — posouzení proveditelnosti

Stav k 21. 10. 2026: průzkum, nikoli hotová nebo na desce ověřená implementace.
Dosavadní YAML, kamera, HuskyLens a media_player zůstávají beze změny.
V této části neproběhla kompilace ani flashování.

Navazující [D1 — test mikrofonu](ETAPA_D1_TEST.md) již má samostatný YAML
a úspěšnou plnou kompilaci. Tento dokument zachycuje původní průzkum;
praktické ověření mikrofonu na desce zatím neproběhlo.

## Co je možné

Vestavěný mikrofon lze číst přes ES8311 a I²S. Zvuk lze následně přenášet
po Ethernetu pro živý poslech a ukládat na PC/NAS/serveru. Samotné přidání
`microphone:` nevytvoří v Home Assistantu přehrávač živého zvuku ani rekordér.
Je potřeba doplnit síťového odesílatele a přijímač.

## Zapojení ověřené ze schématu

Zdroj: [schéma Waveshare, list 1](https://files.waveshare.com/wiki/ESP32-P4-WIFI6-POE-ETH/ESP32-P4-WIFI6-POE-ETH-Schematic.pdf).
Lokální kopie: `investigation/camera/schematic.pdf`; vizuálně prohlédnuté
výřezy `mic-codec.png` a `mic-analog.png` ve stejném adresáři.

| Signál | Zapojení |
|---|---|
| Mikrofon MIC1 | Analogový vstup ES8311, MIC_P/MIC_N |
| ES8311 ASDOUT → vstup ESP32 | GPIO11, budoucí `i2s_din_pin` |
| MCLK | GPIO13 |
| BCLK/SCLK | GPIO12 |
| LRCLK | GPIO10 |
| Výstup ESP32 → ES8311 pro reproduktor | GPIO9, stávající konfigurace |
| I²C řízení kodeku | SDA GPIO7, SCL GPIO8, adresa 0x18 |

Pozor: `use_microphone: true` u ES8311 přepíná vstup na digitální PDM
mikrofon; není to obecné zapnutí mikrofonu. Pro analogový mikrofon této desky
ponechat výchozí `false`. Viz [dokumentace ES8311](https://esphome.io/components/audio_dac/es8311/).
Lokální ESPHome 2026.9.0 v `es8311/es8311.cpp:30` konfiguraci mikrofonní části
volá vždy; řádky 193–198 zapínají analogový vstup a při `use_mic_` navíc PDM.

## Omezení souběhu s hudbou

V místním ESPHome 2026.9.0 mikrofon i reproduktor zamykají stejný `i2s_bus`:

- `.venv/Lib/site-packages/esphome/components/i2s_audio/microphone/i2s_audio_microphone.cpp:98`
- `.venv/Lib/site-packages/esphome/components/i2s_audio/speaker/i2s_audio_speaker_standard.cpp:400`

První návrh proto počítá s vystřídáním přehrávání a snímání. Před spuštěním
mikrofonu musí přehrávač uvolnit sběrnici; před obnovením hudby se snímání zastaví.
Samotné ztlumení reproduktoru sběrnici neuvolní.

[Vývojová dokumentace I²S](https://next.esphome.io/components/i2s_audio/#full-duplex)
již popisuje `full_duplex: true`. Tato volba není v místní verzi 2026.9.0;
nelze ji bez změny verze pouze vložit do YAML. Pro souběh je nutné ověřit
konkrétní verzi implementace a shodné hodinové parametry obou směrů.
Firmware 2026.9.1 na desce nebyl v této etapě znovu sestaven ani otestován.

## Navržený postup

1. **D1 — ověření snímání:** samostatné rozšíření kamerové konfigurace,
   externí I²S mikrofon na GPIO11, bez PDM. Začít s 48 kHz / 16 bit / mono,
   aby parametry odpovídaly stávajícímu ES8311. Správný I²S kanál a vhodný
   zisk potvrdit skutečným záznamem. Hudba během testu zastavená.
   Nejprve ověřit měnící se úroveň zvuku, příjem vzorků a možnost start/stop.
2. **D2 — poslech a nahrávání:** přenos PCM do PC nebo serveru, krátká
   vyrovnávací paměť na ESP32, ukládání WAV na přijímací straně. Jeden
   přijímaný tok může současně sloužit pro poslech i záznam.
3. **D3 — integrace a souběh:** napojení do prostředí HA a případně aktualizace
   pro full duplex. Znovu ověřit kameru, HuskyLens i přehrávání.

Pro síťový přenos je kandidátem VBAN. Existuje externí
[Esphome-VBAN](https://github.com/TheEris/Esphome-VBAN) a
[přijímač v Music Assistantu](https://www.music-assistant.io/plugins/vban-receiver/).
Přijímač umí příchozí tok předat přehrávačům. Kompatibilita externí komponenty
s naším P4, ESP-IDF a mikrofonem zatím ověřená není; nejde o hotové doporučení
k nasazení. Záznam do souboru vyžaduje samostatnou funkci na přijímači.

## Nároky a testy

Mono PCM 48 000 × 16 bit potřebuje přibližně 96 kB/s (768 kbit/s) bez síťové
režie. Minuta záznamu má 5,76 MB, hodina 345,6 MB. Dlouhý záznam proto ukládat
na server, ne do interní flash. PSRAM má sloužit pouze pro omezený buffer.
Skutečná spotřeba RAM, zatížení CPU, zpoždění poslechu a případné výpadky
se změří až při implementaci; dosavadní měření kamery je nepokrývá.

Mikrofon na desce nepoužívá USB host. Přesto může síťový přenos a práce
s buffery ovlivnit kameru. Sledovat fps, volnou paměť, výpadky PCM a odezvu
HuskyLens. Při budoucím full duplexu mikrofon zachytí také vlastní reproduktor;
potlačení ozvěny není automaticky zajištěné.

Očekávaný výsledek budoucího D1 testu: úspěšný start I²S RX, rostoucí počet
vzorků, úroveň reagující na řeč a návrat přehrávání po ukončení snímání.
To jsou kritéria testu, nikoli již naměřené výsledky nebo přesné řetězce logu.
Před nahráním nové varianty provést validaci a plnou kompilaci.

Samostatný zvuk se automaticky nepřipojí k MJPEG obrazu kamery v HA;
společný synchronizovaný obraz se zvukem by vyžadoval další serverovou vrstvu.
Viz také [základní mikrofonní komponenta ESPHome](https://esphome.io/components/microphone/).
