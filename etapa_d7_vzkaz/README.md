# Dveřní zvonek P4 — D7 / 0.2.0

Aktualizace přidává výzvu a desetisekundový hlasový vzkaz ze stávajícího mikrofonu P4, s potvrzením uložení do HA. Firmware se nemění.

**Postup instalace, výběr entit a zkouška tlačítky: [D7-NAVOD.md](D7-NAVOD.md).**

Ze ZIP nahraď pouze `/config/custom_components/p4_doorbell`, restartuj HA a u existující integrace zvol **Konfigurovat**. Integraci neodebírej. Automatika je výchozí vypnutá; nejdřív použij **Výzva a nahrát vzkaz 10 s** na stránce zvonku.

Kód a testy byly připraveny s pomocí OpenAI Codex. Plný průchod v běžícím HA je potřeba ověřit na tvé sestavě. Nic nebylo nasazeno ani flashováno.
