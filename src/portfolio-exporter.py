#!/usr/bin/python3

# Exportiert das Portfolio des Nutzers als CSV-Datei mit ; als Spaltentrenner. Login erfordert ggf. TAN-Eingabe.

from operator import itemgetter,attrgetter
from config import get_allowed_user_ids, get_telegram_token
from onvistabank_api.OnVistaApi import OnVistaApiOTPRequiredException
from onvistabank_api.OnVistaLowLevelApi import OnVistaOTPIsWrongException
from datetime import timedelta
from loguru import logger
import sys
from onvistabank_api.OnVistaApi import OnVistaApi
from config import get_onvistabank_username, get_onvistabank_password
from typing import Optional

def format_number(number: float) -> str:
    return (
        "{:,.2f}".format(number).replace(",", " ").replace(".", ",").replace(" ", ".")
    )

logger.remove(0)

logger.add(sys.stderr, level="ERROR")

api = None

api = OnVistaApi(
    "cookies.txt", get_onvistabank_username(), get_onvistabank_password()
)

try:
    api.login()
except OnVistaApiOTPRequiredException:
    otp = input("Bitte OTP-Passwort eingeben: ")
    api.enterOTP(otp)

# Die Konten dieses Logins abfragen
accounts_result = api.get_accounts()

print("accountNumber;iban;currentBalance;name;isin;quantity;buyingValue;lastValue;totalValue;actualValue;totalPerformance;performancePercentage")
for i, account in enumerate(accounts_result["accountsList"], start=1):
    logger.info("Account: {}", account)

    account_key = account["accountKey"]

    # Die (Aktien-)Positionen für diesen Account abfragen
    positions = sorted(api.trading_positions(account_key)["portfolio"]["positions"], key=itemgetter('isin'))

    for position in positions:
        message = ""
        message += f'{account["accountNumber"]};'
        message += f'{account["iban"]};'
        message += f'{format_number(account["currentBalance"])};'
        
        message += f'{position["name"]};'
        message += f'{position["isin"]};'
        message += f'{position["quantity"]};'

        message += f"{format_number(position['buyingValue'])};"
        message += f"{format_number(position['lastValue'])};"

        message += f"{format_number(position['totalValue'])};"
        message += f"{format_number(position['actualValue'])};"
        
        message += f"{format_number(position['totalPerformance'])};"
        message += f"{format_number(position['performancePercentage'])}"
        #message += "\n"
        print(message)

    print(f"overall actualValue: {format_number(sum([position['actualValue'] for position in positions]))}\n")
    print(f"overall totalPerformance: {format_number(sum([position['totalPerformance'] for position in positions]))}\n")


