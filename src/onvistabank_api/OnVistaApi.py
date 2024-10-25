import logging as log
from loguru import logger
from requests.cookies import cookiejar_from_dict
from onvistabank_api.OnVistaLowLevelApi import OnVistaLowLevelApi


class OnVistaApiOTPRequiredException(Exception):
    def __init__(self):
        super().__init__("An OTP (One-Time-Password) is required to continue.")


# Eine etwas höherlevelige API für den Online-Broker OnVistaBank.
#
# Sie kann in zwei Modi verwendet werden, je nachdem ob der Parameter
# otp_callback gesetzt ist oder nicht. Wenn er gesetzt ist, können
# die Methoden, die mit _with_autologin() enden verwendet werden und es wird
# der otp_callback aufgerufen, wenn ein OTP benötigt wird. Wenn er nicht
# gesetzt ist, muss der Login-Prozess manuell durchgeführt werden. Dafür
# ist der Prozess flexibler.
class OnVistaApi:
    def __init__(self, cookies_file_name, loginName, password, otp_callback=None):
        self.api = OnVistaLowLevelApi(cookies_file_name)
        self.loginName = loginName
        self.password = password
        self.otp_callback = otp_callback

    # Einloggen im System. Wenn ein OTP benötigt wird, wird eine
    # OnVistaApiOTPRequiredException geworfen.
    #
    # Ist auto_generate_otp = True, wird automatisch ein OTP generiert
    # falls einer benötigt wird. Danach muss er mittels enterOTP() eingegeben
    # werden. Ist auto_generate_otp = False, muss ein OTP mittels
    # generateOTP() generiert werden und dann mittels enterOTP() eingegeben
    # werden.
    #
    # Beispielanwendung:
    #
    #   try:
    #       api.login()
    #   except OnVistaApiOTPRequiredException:
    #       otp = input("Bitte OTP-Passwort eingeben: ")
    #       api.enterOTP(otp)
    #
    def login(self, auto_generate_otp=True):
        logger.info("Login with username {} requested...", self.loginName)

        self.api.session_auth_refresh()

        logger.info("Login with username {}", self.loginName)
        login_result = self.api.login(self.loginName, self.password)

        if login_result["otpInfo"]["hasToPassOtp"]:
            if auto_generate_otp:
                self.generateOTP()

            logger.info("Login was attempted, but OTP is required")
            raise OnVistaApiOTPRequiredException()

    # Generiert eine OTP (One-Time-Password) und sendet sie per SMS an den
    # Benutzer. Muss aufgerufen werden nachdem eine OnVistaApiOTPRequiredException
    # geworfen wurde außer es wurde auto_generate_otp = True übergeben, dann
    # wird sie automatisch von login() aufgerufen.
    def generateOTP(self):
        logger.info("Generate One-Time-Password (OTP)")
        return self.api.generateOTP()

    # OTP in das System eingeben, sodass der Benutzer authentifiziert werden kann.
    def enterOTP(self, otpToken):
        logger.info(f"Check One-Time-Password (OTP): Supplied is {otpToken}")
        return self.api.checkOTP(otpToken)

    def _autologin_if_needed(self):
        self.api.session_auth_refresh()
        login_result = self.api.login(self.loginName, self.password)

        if login_result["otpInfo"]["hasToPassOtp"]:
            log.info("Generate One-Time-Password (OTP)")
            self.api.generateOTP()

            token = self.otp_callback()

            log.info(f"Check One-Time-Password (OTP): Supplied is {token}")
            self.api.checkOTP(token)

    def _try_with_autologin(self, block):
        try:
            return block({})
        except (OnVistaAccessDeniedException, OnVistaPerformanceDataError):
            self._autologin_if_needed()
            return block({})

    # Im automatischen Modus wird damit der Login-Prozess ausgelöst.
    def trigger_login(self):
        self._autologin_if_needed()

    # Gibt die Konten des eingeloggten Benutzers zurück. (Autologin-Modus)
    def get_accounts_with_autologin(self):
        return self._try_with_autologin(lambda params: self.api.getAccounts())

    # Gibt die Positionen für ein Konto mit
    # dem angegebenen Account-Key
    # des eingeloggten Benutzers zurück. (Autologin-Modus)
    def trading_positions_with_autologin(self, account_key):
        return self._try_with_autologin(
            lambda params: self.api.tradingPositions(account_key)
        )

    # Gibt die Konten des eingeloggten Benutzers zurück.
    def get_accounts(self):
        return self.api.getAccounts()

    # Gibt die Positionen für ein Konto mit
    # dem angegebenen Account-Key
    # des eingeloggten Benutzers zurück.
    def trading_positions(self, account_key):
        return self.api.tradingPositions(account_key)
