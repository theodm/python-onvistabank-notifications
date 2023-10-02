# Eine Datei zum schnellen Testen der OnVistaApi ganz ohne Telegram-Bot
# oder ähnliches.

from onvistabank_api.OnVistaApi import OnVistaApi
from config import get_onvistabank_username, get_onvistabank_password
from loguru import logger

# Hier wird das OTP direkt über die Konsole eingegeben und
# direkt von der Klasse OnVistaApi abgefragt. Dafür sind die Methoden
# mit _with_autologin() am Ende, zu verwenden. Dann braucht der
# Login-Prozess nicht manuell durchgeführt werden.
api = OnVistaApi(
    "test.cookies",
    get_onvistabank_username(),
    get_onvistabank_password(),
    lambda: input("Bitte OTP-Passwort ausgeben: "),
)

api.trigger_login()

accounts_result = api.get_accounts_with_autologin()
for account in accounts_result["accountsList"]:
    logger.info("Account: {}", account)

    account_key = account["accountKey"]

    # Die (Aktien-)Positionen für diesen Account abfragen
    positions = api.trading_positions_with_autologin(account_key)["portfolio"][
        "positions"
    ]

    message = "\n"
    # message += f"IBAN: {account['iban']}\n"
    message += f"Kaufkraft: {account['buyPower']} EUR\n"
    message += f"Kontostand: {account['currentBalance']} EUR\n"
    message += "\n"

    for position in positions:
        message += "\n"
        message += f'{position["name"]} (ISIN: {position["isin"]})\n'
        message += f'Anzahl: *{position["quantity"]} Anteile*\n'
        message += "\n"

        message += "Werte pro Anteil:\n"
        message += f"Kaufwert: *{position['buyingValue']:.2f} EUR*\n"
        message += f"Aktueller Wert: *{position['lastValue']:.2f} EUR*\n"
        message += "\n"

        message += "Performance (heute)\n"
        message += f"absolut: *{position['dailyTotalPerformance']:.2f} EUR*\n"
        message += f"relativ: *{position['dailyPerformancePx']:.2f} %*\n"
        message += "\n"

        message += "Performance (gesamt)\n"
        message += f"Kaufwert: *{position['totalValue']:.2f} EUR*\n"
        message += f"Aktueller Wert: *{position['actualValue']:.2f} EUR*\n"
        message += f"absolut: *{position['totalPerformance']:.2f} EUR*\n"
        message += f"relativ: *{position['performancePercentage']:.2f} %*\n"
        message += "\n"

    print(message)
