# Etapa D3 — vzkazy návštěvy: text a původní hlas přes Assist

Posouzení k 21. 10. 2026. HA OS v Proxmoxu, uživatel již používá převod řeči
na text. Konkrétní STT/TTS poskytovatel a jeho nastavení zatím nejsou známé.
Ověřena dokumentace a zdroj HA Core 2026.10.2, lokální ESPHome 2026.9.0.
Veřejná dokumentace ESPHome již ukazuje 2026.10.0; dostupnost voleb v našem
sestavení byla proto kontrolována i v místním kódu.

Aktualizace 22. 10.: následuje [připravená varianta a návod D3](ETAPA_D3_PRIPRAVA.md).
Níže je zachovaný průzkum před implementací; aktuální stav ověření je v novém návodu.

## Doporučení

**Pro první nasazení použít textový vzkaz přes standardní Assist satellite
a akci `assist_satellite.ask_question`, bez seznamu odpovědí.** Přepis uložit
do textového souboru pomocí vestavěné integrace File a zobrazit jako oznámení.
Pro poslech a doladění mikrofonu dočasně zapnout vestavěné WAV nahrávky Assistu.

Nový přijímací doplněk, GitHub repozitář ani nový server pro tuto cestu
nejsou potřeba. Již připravená HTTP/WAV varianta D2 zůstává jako experimentální
alternativa; není nutné pokračovat v její instalaci.

## Co lze získat

| Varianta | Text | Původní hlas | Změny mimo ESP32 | Hodnocení |
|---|---|---|---|---|
| Assist `ask_question` + File + oznámení | Ano | Běžně se nearchivuje | Skript a vestavěná integrace v HA | Doporučený základ |
| Totéž + diagnostické nahrávky Assist | Ano | WAV pro kontrolu | Nastavení HA a restart | Vhodné pro test, ne hotový archiv |
| D2 vlastní WAV přijímač | Ne, STT by se přidávalo | Přesný 10s WAV | Instalace přijímače | Funkční lokální test a kompilace, ale zbytečná instalační práce pro text |
| WAV ke stažení z ESP32 | Bez doplnění STT ne | Návrhově ano | Stahování a archivace v HA | Jen dříve navržená možnost, neimplementováno |

## Text bez ovládání domu

`ask_question` přehraje otázku nebo výzvu a zachytí odpověď. Pokud se vynechá
`answers`, vrací volný přepis v `response_variable.sentence`. Není potřeba
vymýšlet seznam možných vzkazů. Zdroj: [oficiální akce](https://www.home-assistant.io/actions/assist_satellite.ask_question/).

Ověření v [HA 2026.10.2, assist_satellite/entity.py](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/components/assist_satellite/entity.py):
řádek 380 vrací při prázdném seznamu celý přepis; řádky 482–485 nastavují
pro čekající otázku konec pipeline na STT. Tím se přeskočí vyhodnocování
záměru i následná odpověď asistenta. To je vhodnější než běžné spuštění
hlasového asistenta a pokus jej zastavit až v ESPHome `on_stt_end`.
Zastavení po události není spolehlivá hranice proti vykonání příkazu.

Návrh bude spouštět pouze tuto otázku z HA, bez wake word a bez průběžného
naslouchání. Samostatnou automatizaci odemykání přes HuskyLens nepropojovat
s obsahem vzkazu. Zvolený režim ověřit v trace: nesmí následovat `intent-start`.

Ilustrační část budoucího HA skriptu, **ne konfigurace již existující entity**:

```yaml
- action: assist_satellite.ask_question
  data:
    entity_id: assist_satellite.NAHRADIT_SKUTECNOU_ENTITOU
    question: "Prosím, řekněte krátký vzkaz pro majitele."
    preannounce: false
  response_variable: vzkaz
- action: persistent_notification.create
  data:
    title: "Vzkaz od dveří"
    message: "{{ vzkaz.sentence }}"
```

Tento příklad není hotová automatizace: doplní se ověření neprázdného přepisu,
obsluha timeoutu/chyby, archivace a cílový telefon. Akce má vlastní parametr
`data.entity_id`, nikoli `target.entity_id`. Délka odpovědi se řídí detekcí
konce řeči a timeouty, není to pevný desetisekundový rekordér.

## Kam ukládat text

Vestavěná [integrace File](https://www.home-assistant.io/integrations/file/)
umí přidávat zprávy do souboru přes `notify.send_message`. Navrhuji např.
`/config/vzkazy/navstevy.txt`, s časovým razítkem. Adresář musí existovat
a být povolený v `homeassistant.allowlist_external_dirs`; File se nastavuje
v UI integrací, nepotřebuje vlastní doplněk. Soubor a jeho zálohy/velikost
budou součástí provozního nastavení.

Pro pohodlné čtení přidat oznámení v HA a případně Companion aplikaci.
Oznámení není náhrada archivu. `input_text` nepoužívat jako jediné úložiště
celého vzkazu: stav má nejvýše 255 znaků. Viz [Input text](https://www.home-assistant.io/integrations/input_text/).
Přepis může mít chyby ve jménech, číslech a při hluku; není totožný s originálním hlasem.

## Jak uložit skutečný hlas bez vlastního přijímače

HA oficiálně podporuje `assist_pipeline.debug_recording_dir`. Příklad pro
dočasné ladění podle [návodu HA](https://www.home-assistant.io/voice_control/troubleshooting/#to-tweak-the-assist-audio-configuration-for-your-device):

```yaml
assist_pipeline:
  debug_recording_dir: /share/assist_pipeline
```

Po restartu vznikají WAV nahrávky běhů Assistu. Pro první kontrolu mikrofonu
je to nejjednodušší cesta k původnímu zvuku. Není to syntetické přečtení textu.

Zdroj [HA 2026.10.2, assist_pipeline/run.py](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/components/assist_pipeline/run.py#L345)
potvrzuje globální nastavení adresáře, podadresáře podle zařízení/pipeline
a běhu; od řádku 424 zapisuje WAV. Samotný zapisovač neřeší promazávání
archivu ani omezení jen na dveřní zařízení. Zapnutí proto může zaznamenávat
i další hlasové asistenty. `ask_question` vrací přepis, nikoli odkaz na WAV.

Pro trvalé ukládání hlasu by bylo nutné doplnit výběr nahrávek dveřního
zařízení, spojení s textem, uchování např. 7 dní a obsluhu neúplných běhů.
To není hotová standardní funkce hlasové schránky. Přesměrování diagnostiky
do např. `/media/assist_debug` vyplývá z podpory obecné cesty v kódu, ale
je třeba je ověřit na HA OS. WAV by tam šel procházet v médiích; struktura
adresářů však zůstává diagnostická a není slibovaným stabilním archivním API.

## Co je potřeba upravit na našem ESP32-P4

Přenos mikrofonu do HA již řeší oficiální [ESPHome Voice Assistant](https://esphome.io/components/voice_assistant/).
Výstup lze navázat na existující media_player. Podporu oznámení a navazujícího
snímání dokládá lokální `voice_assistant.h`, řádky 145–166; HA ESPHome
[implementace satelitu](https://github.com/home-assistant/core/blob/2026.10.2/homeassistant/components/esphome/assist_satellite.py)
podporované schopnosti přebírá a realizuje výzvu následovanou pipeline.
Reprodukce a mikrofon se mohou vystřídat, full duplex není pro tento scénář nutný.

**Konkrétní technický bod:** lokální `voice_assistant/__init__.py:196`
vyžaduje mikrofonní zdroj **16 kHz**. Ověřený D1 mikrofon a kodek běží
na **48 kHz**; samotné přidání `voice_assistant:` proto nestačí.
`MicrophoneSource` umí změnit bitovou hloubku a vybrat kanál, ale v místním
kódu není převzorkování frekvence.

Pro zachování hudby a současného nastavení ES8311 doporučuji malý lokální
adaptér mikrofonu **48 → 16 kHz s filtrem proti aliasingu**, který bude
předkládat data standardnímu Voice Assistantu. Nenahrazuje síťový protokol
a nevyžaduje instalaci v HA. Jeho implementace a kompilace teprve následují.
Pouhé označení 48kHz dat jako 16kHz ani vynechání každých dvou vzorků bez
filtru nejsou správné řešení. Alternativou je přeladění celé audio větve
na 16 kHz; to by ale zasáhlo do ověřeného přehrávání, proto ji teď nevolím.

## Navržené další kroky a podmínky úspěchu

1. **D3a:** nová samostatná ESPHome varianta, adaptér mikrofonu, standardní
   voice_assistant a vazba na stávající media_player. Validace, generování
   C++ a plná kompilace; původní soubory zachovat.
2. **D3b:** v HA vybrat českou pipeline se stávajícím STT. Ověřit také TTS
   pro výzvu; pokud není, použít nahranou výzvu přes `question_media_id`.
   Ručně spustit `ask_question`, vrátit přepis a uložit ho přes File.
3. **D3c:** na omezenou dobu zapnout diagnostické WAV, poslechnout kvalitu
   a porovnat řeč s přepisem. Ověřit kameru, HuskyLens a návrat přehrávání.
4. Až poté napojit zvonkové tlačítko, oznámení telefonu a případný trvalý
   archiv hlasu. Testovat ticho, delší pauzu, hluk, výpadek STT, opakované
   zazvonění a větu ve tvaru příkazu; nesmí se vykonat akce v domě.

## Stav a hranice ověření

Ověřeno ze zdrojů: volný přepis v odpovědi otázky, ukončení na STT, File
pro textový soubor, diagnostické WAV a požadavek 16 kHz. D1 na desce prokázal
vzorky a souběh s kamerou. **Nová Assist varianta zatím není implementovaná
ani zkompilovaná; nebyla měněna konfigurace HA ani flashován firmware.**
Přesná kvalita, délka zachyceného vzkazu a práce českého STT musí projít
praktickým testem. Cloudové či lokální zpracování záleží na již zvoleném
STT poskytovateli, kterého ještě neznáme.
