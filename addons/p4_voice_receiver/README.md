# P4 hlasové vzkazy

Lokální přijímač pro experimentální komponentu ESPHome `voice_recorder`.
Ukládá desetisekundové mono WAV (48 kHz, 16 bit) do `/media/vzkazy`.
Přehrávání je přes přihlášený Home Assistant: **Média → Moje média → vzkazy**.

## Instalace v Home Assistant OS

1. ZIP nejprve rozbalte na PC. Uvnitř je složka `p4_voice_receiver`.
   Přes Samba share otevřete sdílení HA OS (ve Windows například
   `\\homeassistant.local`). Aktuální HA používá sdílenou složku **local_apps**;
   zkopírujte do ní rozbalenou složku `p4_voice_receiver`. Výsledek musí být
   `/local_apps/p4_voice_receiver/config.yaml` a vedle něj `Dockerfile` a `server.py`.
   Nevklejte samotný ZIP a nevytvářejte dvojité vnoření `p4_voice_receiver/p4_voice_receiver`.
   U starších verzí Samba/Supervisoru může být skutečně dostupné sdílení **addons**;
   tehdy použijte jeho kořen. Složku s druhým názvem nevytvářejte naslepo.
   Nejde o podadresář `/config` ani o soubory na hostiteli Proxmox.
2. V HA otevřete **Nastavení → Aplikace → Instalovat aplikaci** (starší UI:
   **Nastavení → Doplňky → Obchod s doplňky**). Nabídka ⋮ → kontrola aktualizací,
   potom obnovte stránku. V části **Místní aplikace / Local apps** najděte
   **P4 hlasove vzkazy** a instalujte.
   První instalace sestaví kontejner a potřebuje internet pro základní obraz.
3. Vygenerujte náhodný klíč o 64 malých hexadecimálních znacích, například
   v Pythonu na PC:

   ```sh
   python -c "import secrets; print(secrets.token_hex(32))"
   ```

4. Klíč vložte do položky `token` v konfiguraci doplňku. Stejný klíč vložte
   do ESPHome `secrets.yaml` jako `voice_receiver_token`. Není to API klíč HA.
5. Ponechte síťový port 8099 a `max_recordings: 100`. Spusťte doplněk.
   Log má obsahovat `Receiver ready on port 8099; destination /media/vzkazy`.
6. Ve firmware nastavte `voice_receiver_ip` na IPv4 adresu **virtuálního
   počítače HA OS**, nikoli Proxmoxu, ESP32 nebo interní adresu kontejneru.

Podrobnosti firmware a testu jsou v `ETAPA_D2_VZKAZY.md` v kořeni projektu.

### Když se aplikace nezobrazí nebo instalace selže

- Ověřte skutečné sdílení `local_apps` (případně starší `addons`) a přímou
  přítomnost tří souborů ve složce přijímače. `config.yaml` nesmí mít příponu `.txt`.
- Po kontrole aktualizací zkuste obnovení prohlížeče Ctrl+F5.
- V **Nastavení → Systém → Protokoly** vyberte **Supervisor**. Chyba se jménem
  `p4_voice_receiver` určí, zda jde o rozpoznání konfigurace, nebo sestavení obrazu.
- Po instalaci používejte log přímo na stránce přijímače. Prázdný nebo nesprávně
  dlouhý `token` spuštění odmítne; vložte vlastní 64znakový hexadecimální klíč.
- Tento ZIP se nepřidává jako URL repozitáře do obchodu ani jako integrace zařízení.

Oprava původního návodu: cesta `/addons` není univerzální pro aktuální HA.
Oficiální postup aktualizovaný v říjnu 2026 uvádí `/local_apps`.

## Provoz

- Přijímá pouze `POST /recordings`, s hlavičkou `Authorization: Bearer …`,
  typem `application/octet-stream` a přesně 960 000 bajty PCM S16LE mono 48 kHz.
- Nahrávka se publikuje až po úplném přenosu a uzavření WAV. HTTP 201 potvrzuje
  zápis; neúplný přenos se zahodí. K souborům doplněk neposkytuje webový přístup.
- Název obsahuje čas **UTC** a náhodnou příponu. Například čas 15:30 UTC
  odpovídá v Praze během letního času 17:30. WAV má 960 044 bajtů.
- Při dosažení limitu nahrávek se další odmítají (507); staré soubory se
  automaticky nemažou. Před zvýšením limitu nebo dalším záznamem je archivujte
  nebo odstraňte ze složky médií. Výchozích 100 souborů zabere přibližně 96 MB.
- Pouze důvěryhodná místní síť: přenos HTTP není šifrovaný. Token chrání příjem
  před požadavky bez klíče, nechrání zvuk proti odposlechu sítě. Port nevystavujte
  do internetu. Používá se `/media`, nikoli veřejná složka `/config/www`.
- Po chybě sítě může být soubor uložený, i když deska nedostala potvrzení.
  Než pokus zopakujete, podívejte se do médií. Automatické opakování není zapnuté.

## Ověření

Síťové testy přijímače lze spustit pomocí `python test_server.py` z kopie projektu
na PC. Docker obraz a instalaci v Supervisoru je nutné ověřit na HA OS;
lokálně nebyl dostupný Docker. Toto není oficiální doplněk Home Assistantu.

Zdroje: [lokální doplňky](https://contributors.home-assistant.io/apps/first-app/),
[konfigurace a mapování médií](https://contributors.home-assistant.io/apps/reference/configuration/),
[média HA OS](https://www.home-assistant.io/more-info/local-media/setup-media/).
