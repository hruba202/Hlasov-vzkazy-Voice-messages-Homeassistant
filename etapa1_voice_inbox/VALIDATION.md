# Ověření etapy 1 — 25. 10. 2026

## Aktuální oprava 0.3.1

- Opraven souběh registrace společných HTTP cest a panelu při startu více zdrojů.
- Koordinátor explicitně oddělen od config entry prvního zdroje. Používá
  `async_refresh` a vlastní shutdown při vypnutí HA, nikoli entry-only první refresh.
- 8 testů `tests/test_lifecycle_standalone.py`: PASS. Provádějí skutečné funkce
  integrace načtené přes AST proti náhradám HA API s asynchronním přepínáním;
  nejde o spuštění HA ani jeho HTTP serveru. Scénáře: tři souběžné zdroje,
  sekvenční přidání a reload prvního zdroje, unload všech a nový setup,
  samostatný souběh registrace stránky, retry po chybě statických cest,
  rollback platformy, odmítnutý unload a zotavení po chybě úložiště.
- Ověřena syntaxe Python/JSON a čistota balíčku. Žádné nové balíčky neinstalovány.
- Živé ověření 0.3.1 v HA: ČEKÁ NA UŽIVATELE. Nic nenasazeno a firmware nezměněn.
- Nutný plný restart HA po výměně souborů, aby zmizel původní stav registrace cest.

Použité API ověřeno ve zdroji
[HA 2026.10.3 update_coordinator](https://github.com/home-assistant/core/blob/2026.10.3/homeassistant/helpers/update_coordinator.py):
explicitní `config_entry=None`, `async_register_shutdown` a `async_refresh`.

Následují historické výsledky předchozích verzí.

Provedeno bez instalace balíčků, bez zápisu do HA a bez zásahu do firmware.

- Python 3.14.2 ve stávajícím prostředí projektu.
- 14 standardních unittest testů: PASS. Zahrnují obě frekvence, PCM/WAV,
  metadata, délku, velikost, cestu, chyby disku, atomické přejmenování a úklid,
  globální kvótu při souběžných zápisech, klíče, LAN a omezení chybných pokusů.
- AST parsování Pythonu a načtení JSON: PASS.
- HTTP testy a testy config flow: PŘIPRAVENÉ, NESPUŠTĚNÉ. Závislosti nejsou
  dostupné a uživatel výslovně požaduje nic neinstalovat.
- Kompletní start v HA Core 2026.10.3, UI config flow, skutečný zápis do /media,
  curl z PC a skutečné odmítnutí Nabu Casa: NEOVĚŘENO.

Tento balíček je připravený k dalšímu testování. Neoznačujeme ho za živě ověřenou
integraci. Nic se samo nenasazuje. Před nasazením dokončit HTTP testy a získat
výslovné potvrzení uživatele.

Verze 0.1.1: doplněn úspěšný test mediálního adresáře s identifikátorem jiným
než local a správného media-source odkazu. Živý setup v HA zůstává neověřený.

## Aktualizace 0.2.0

Entity a upozornění na kvótu implementovány. Na pokyn uživatele nebyly spuštěny
nové testy. Výše uvedené výsledky platí pro předchozí verzi. Kontrolována pouze
syntaxe Python/JSON a explicitní seznam ZIP. Živé ověření HA neprovedeno.

## Aktualizace 0.3.0 — stránka Hlasové vzkazy

Přidáno nahrávání mikrofonem prohlížeče, uložení přes autentizovaný HTTP endpoint
a přehrání souboru zpětně z HA. Přístup jen pro správce. Stejné limity ukládání,
kvóta a událost jako u ESP; jeho LAN/klíčová autorizace se nemění.

Kontrola syntaxe Python/JSON/JavaScript a čistoty ZIP; bez instalace závislostí.
Automatické testy na pokyn uživatele nyní nespouštěny. Záznam mikrofonu, celý start
HA, průchod přes Nabu Casa a přehrání v prohlížeči musí potvrdit ruční pokus
v HA. Tento balíček nebyl nasazen a firmware nebyl změněn.
