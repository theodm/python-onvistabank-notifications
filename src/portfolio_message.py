class OTPRequiredException(Exception):
    def __init__(self):
        super().__init__("An OTP (One-Time-Password) is required to continue.")


class OTPWrongException(Exception):
    def __init__(self):
        super().__init__("The OTP (One-Time-Password) is wrong.")


# Eine Fließkommazahl wird im deutschen für Geldbeträge üblichen Format formatiert und
# auf zwei Nachkommastellen gerundet. Dabei werden für Tausender Punkte und für Dezimalstellen
# Kommas verwendet.
#
# Beispiele:
#   1234567.89 -> 1.234.567,89
#   1234567.8 -> 1.234.567,80
#   1234567 -> 1.234.567,00
def format_number(number: float) -> str:
    return (
        "{:,.2f}".format(number).replace(",", " ").replace(".", ",").replace(" ", ".")
    )


# Gibt für einen Account bei der OnVistaBank alle verknüpften Konten
# und deren Positionen sowie die Gesamtperformance und weitere Daten
# in einer Nachricht im Markdown-Format zurück. Diese kann dann so als
# Telegram-Nachricht verschickt werden.
#
# Im ersten Aufruf muss keine TAN übergeben werden. Wenn der Server
# eine TAN anfordert, wird eine OTPRequiredException geworfen. In diesem
# Fall muss die Funktion erneut aufgerufen werden und die TAN übergeben
# werden. Wenn die TAN falsch ist, wird eine OTPWrongException geworfen.
#
# Beispielanwendung:
#
#   try:
#       message = get_portfolio_message_markdown(api)
#   except OTPRequiredException:
#       message = get_portfolio_message_markdown(api, tan)
#
def get_portfolio_message_markdown(api: OnVistaApi, tan: Optional[str] = None):
    try:
        if tan:
            try:
                api.enterOTP(tan)
            except OnVistaOTPIsWrongException:
                raise OTPWrongException()

        api.login()
    except OnVistaApiOTPRequiredException:
        raise OTPRequiredException()

    res = api.get_accounts()

    # Die Konten dieses Logins abfragen
    accounts_result = api.get_accounts()
    for i, account in enumerate(accounts_result["accountsList"], start=1):
        logger.info("Account: {}", account)

        account_key = account["accountKey"]

        # Die (Aktien-)Positionen für diesen Account abfragen
        positions = api.trading_positions(account_key)["portfolio"]["positions"]

        message = "\n"
        message += f"*Konto {i}* ({account['iban'][-3:]})\n"
        message += f"Kaufkraft: {format_number(account['buyPower'])} EUR\n"
        message += f"Kontostand: {format_number(account['currentBalance'])} EUR\n"
        message += f"Gesamtwert: {format_number(sum([position['actualValue'] for position in positions]) + account['currentBalance'])} EUR\n"

        for position in positions:
            message += "\n"
            message += f'{position["name"]} (ISIN: {position["isin"]})\n'
            message += f'Anzahl: *{position["quantity"]} Anteile*\n'
            message += "\n"

            message += "Werte pro Anteil:\n"
            message += f"Kaufwert: *{format_number(position['buyingValue'])} EUR*\n"
            message += f"Aktueller Wert: *{format_number(position['lastValue'])} EUR*\n"
            message += "\n"

            message += "Performance (heute)\n"
            message += (
                f"absolut: *{format_number(position['dailyTotalPerformance'])} EUR*\n"
            )
            message += f"relativ: *{format_number(position['dailyPerformancePx'])} %*\n"
            message += "\n"

            message += "Performance (gesamt)\n"
            message += f"Kaufwert: *{format_number(position['totalValue'])} EUR*\n"
            message += (
                f"Aktueller Wert: *{format_number(position['actualValue'])} EUR*\n"
            )
            message += f"absolut: *{format_number(position['totalPerformance'])} EUR*\n"
            message += (
                f"relativ: *{format_number(position['performancePercentage'])} %*\n"
            )

    return (
        message.replace(".", "\.")
        .replace("(", "\(")
        .replace(")", "\)")
        .replace("-", "\-")
        .replace("+", "\+")
        .replace("!", "\!")
        .replace("=", "\=")
    )
