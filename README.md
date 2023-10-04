# python-onvistabank-notifications

Diese Anwendung ermöglicht es die aktuellen Informationen eines OnVistaBank-Depots wie den Kontostand und den Wert der Positionen abzurufen. Dafür verwendet die Anwendung die interne API, welche auch vom Webtrading-Interface (https://webtrading.onvista-bank.de) verwendet wird. Die entsprechenden API-Funktionen wurden mittels Reverse-Engineering ausgemacht. Die Ausgabe erfolgt in diesem Fall mittels eines Telegram-Bots, der es ermöglicht, die aktuellen Informationen zum Depot auszugeben.

![Ein Screenshot der Konversation mit dem Telegram-Bot. Sie zeigt die Nachricht im Telegram-Web-Interface, die der Telegram-Bot an den Benutzer sendet. Sie enthält die Konten des Depots sowie deren Bestand (Kaufkraft, Kontostand, Gesamtwert) sowie die Informationen zu den einzelnen Positionen (Name, Kaufwert, Aktueller Wert, Performance heute, Performance gesamt).](docs/app_preview.png)

Hier wird nur ein Ausschnitt der API implementiert. Dabei werden die folgenden Funktionalitäten verwendet:

- Authentifizierung (insbesondere OTP-Verfahren)
- Abruf der Konten
- Abruf der Positionen zu einem Konto

Die Anwendung kann um die anderen Funktionalitäten der Webtrading-API (z.B. Kauf und Verkauf von Positionen) erweitert werden und kann damit als Basis für weitere Experimente dienen. 

## Konfiguration

Es sind die entsprechenden Variablen in der secrets.properties zu setzen. Diese muss sich im Root-Ordner der Anwendung befinden. Als Vorlage steht die Datei secrets.properties.rename zur Verfügung.

```
# This is a properties file to store secret values
# Rename this file to secrets.properties and replace the example value with your own token

[secrets]
# api token for the telegram bot
TELEGRAM_API_TOKEN = 123456789:ABCDEFGHIJKLMNOPQRSTUVWXYZ
# only these users are allowed to receive messages with confidential information
ALLOWED_USER_IDS = 123456789,987654321

# username for onvistabank broker
ONVISTABANK_USERNAME = XM662565
# password for onvistabank broker
ONVISTABANK_PASSWORD = 90823843

# Deployment configuration, recommended to install it on a device
# which is protected by a firewall, to prevent unauthorized access
# to your bank username and password (see above)
DEPLOY_REMOTE_HOST = 10.12.5.24
DEPLOY_REMOTE_USER = pi
DEPLOY_REMOTE_PASSWORD = 1234
```

Die Variable TELEGRAM_API_TOKEN muss mit dem Token des Telegram-Bots ersetzt werden. Dieser kann über den BotFather (https://t.me/botfather) erstellt werden. Weitere Informationen dazu finden sich in der Telegram-Dokumentation (https://core.telegram.org/bots).

Die Variable ALLOWED_USER_IDS gibt an, welche Benutzer die Nachrichten, die ja vertrauliche Informationen enthalten, erhalten dürfen. Diese Liste ist kommasepariert und muss mit den User-IDs der Benutzer ersetzt werden. Die User-ID kann über den Telegram-Bot @userinfobot (https://t.me/userinfobot) ermittelt werden.

Die Variablen ONVISTABANK_USERNAME und ONVISTABANK_PASSWORD müssen mit den Zugangsdaten für das OnVistaBank-Depot des Webtrading ersetzt werden.

Die Variablen DEPLOY_REMOTE_HOST, DEPLOY_REMOTE_USER und DEPLOY_REMOTE_PASSWORD sind nur notwendig, falls das Deployment-Skript im Unterordner /deploy verwendet wird. Dies wird an anderer Stelle beschrieben.

## Installation
Für die Installation ist Python 3.11 und das Tool pipenv notwendig. Die Installation erfolgt wie folgt:

```
pipenv install
```

## Ausführung
Die Anwendung wird wie folgt ausgeführt:

```
pipenv run python ./src/main.py
```

## Verwendung
Sobald der selbst erstellte Telegram-Bot gestartet wurde und in der eigenen Freundesliste hinzugefügt wurde, kann dieser über die Telegram-App verwendet werden. 

Der Telegram-Bot bietet die folgenden Befehle an:

- /portfolio
- /cancel

Der Befehl /portfolio gibt die aktuellen Informationen zum Depot aus, wie sie im Screenshot oben zu sehen sind. Sollte die Authentifizierung mittels OTP-Verfahrens (One-Time-Password) notwendig sein, so wird der Benutzer aufgefordert, den OTP-Code einzugeben. Dieser wird von der OnVisaBank generiert und dem Benutzer mittels SMS gesendet. Der Befehl /cancel bricht die Authentifizierung ab.

Zusätzlich gibt der Bot die Informationen, wie sie /portfolio bereitstellen würde, einmal monatlich automatisch aus; sofern eine Authentifizierung bereits stattgefunden hat.

## Webtrading-API
Die Webtrading-API läuft über HTTP und den Endpunkt https://webtrading.onvista-bank.de/services/api/ und verwendet JSON als Datenformat. Die API ist in verschiedene Domänen unterteilt, die jeweils einen eigenen Service anbieten. Gepackt wird das in eine eigene JSON-Struktur. Für Detailinformationen ist die Methode low_level_request in der Datei OnVistaLowLevelApi.py relevant.

Die hier implementierten Domänen und Services sind:
 - Session_Auth
    - login
    - refresh
 - Session_Otp
    - generateOtp
    - checkOtp
 - Bank_Account
    - getAccountsList

Weitere Informationen sind der OnVistaApi.py und OnVistaLowLevelApi.py zu entnehmen.

## Deployment
Es wird das Deployment auf einen von außen nicht zugreifbaren Webserver, zum Beispiel einem Raspberry Pi in einem eigenen Haushalt hinter einer Firewall empfohlen, da die hinterlegten Konfigurationen sensitiv sind. 

Das Deployment erfolgt mittels der Datei deploy/deploy.py. Diese verwendet die Variablen DEPLOY_REMOTE_HOST, DEPLOY_REMOTE_USER und DEPLOY_REMOTE_PASSWORD aus der secrets.properties. Diese müssen entsprechend gesetzt werden. Dann erfolgt das Deployment auf ein Raspbian-System. Python und pipenv werden installiert, falls benötigt und ein SystemD-Service wird erstellt.
