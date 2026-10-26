# Dveřní zvonek P4 — D8 / 0.3.0

Aktualizace přidává fyzické tlačítko zvonku a režim, kdy se po výzvě čeká na další stisk pro zahájení záznamu. Stisk během nahrávání vzkaz uloží.

**Aktuální postup instalace, zapojení GPIO2 a zkouška: [D8-NAVOD.md](D8-NAVOD.md). Výsledky ověření: [OVERENI.md](OVERENI.md).**

Ze ZIP nahraď `/config/custom_components/p4_doorbell`, restartuj HA a u existující integrace zvol **Konfigurovat**. Integraci neodebírej. Nejdřív použij **Stisk tlačítka zvonku (zkouška)** na stránce zvonku, bez flashování. Režim čekání na tlačítko je nutné v nastavení zapnout.

Nový soubor `esp32p4-doorbell-button.yaml` patří vedle stávajících souborů D5. Přidává jen GPIO vstup, bez změny audia, kamery a HuskyLens. Testovací kompilace používá oddělené testovací údaje; takovou binárku neflashuj. Pro nasazení použij vlastní secrets a nejprve dokonči plnou kompilaci.

Kód a testy byly připraveny s pomocí OpenAI Codex. Plný průchod v běžícím HA je potřeba ověřit na tvé sestavě. Nic nebylo nasazeno ani flashováno.
