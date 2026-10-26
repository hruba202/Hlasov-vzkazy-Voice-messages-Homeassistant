# Diagnostická oprava 0.1.1

Po stisku Zazvonit z P4 se zobrazovala obecná chyba, která skrývala skutečnou výjimku HA. Verze 0.1.1 zobrazí její text a případný identifikátor chyby přímo na stránce a zapíše je do protokolu `custom_components.p4_doorbell`. Vypršení časového limitu má samostatnou hlášku.

**Toto opravuje diagnostiku, nikoli zatím neznámou příčinu neúspěšného hovoru.** Kamera i panel podle uživatelského snímku fungují. Samotné vyzvánění dosud potvrzeno nebylo. Volání ani firmware se touto opravou nemění.

1. Ze ZIP `D6-zvonek-0.1.1.zip` nahraď jen složku `/config/custom_components/p4_doorbell`.
2. Restartuj HA a znovu načti stránku Dveřní zvonek. Integraci neodebírej; výběr zařízení a skupina zůstanou stejné.
3. Jednou stiskni Zazvonit z P4 a pošli nové přesné chybové hlášení. Opakované stisky příčinu nevyřeší.

Lokálně prošlo 10 testů řídicí logiky, dva testy zpracování chyb HTTP view a kontrola syntaxe. Testy používají simulované rozhraní HA. V uživatelově HA nebylo nic instalováno ani změněno.
