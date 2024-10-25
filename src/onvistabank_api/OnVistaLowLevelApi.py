import requests as req
import logging as log
import json
import certifi
import urllib3

from loguru import logger

from requests.cookies import cookiejar_from_dict


# Exceptions und Fehler-Codes der OnVista-API
class OnVistaException(Exception):
    def __init__(self, code, message):
        self.code = code
        self.message = message

    def __str__(self):
        return f"{self.code}: {self.message}"


class OnVistaPerformanceDataError(OnVistaException):
    def __init__(self, message):
        super(OnVistaPerformanceDataError, self).__init__(50302, message)


class OnVistaAccessDeniedException(OnVistaException):
    def __init__(self, message):
        super(OnVistaAccessDeniedException, self).__init__(1002, message)


# Fehlercode: 111003 wenn der OTP-Code falsch ist
class OnVistaOTPIsWrongException(OnVistaException):
    def __init__(self, message):
        super(OnVistaOTPIsWrongException, self).__init__(111003, message)


def make_onvista_exception(code, message):
    if code == 1002:
        return OnVistaAccessDeniedException(message)
    if code == 50302:
        return OnVistaPerformanceDataError(message)
    if code == 111003:
        return OnVistaOTPIsWrongException(message)

    return OnVistaException(code, message)


# Die Low-Level-API für den Online-Broker der OnVistaBank. Diese API ist nicht für den direkten
# Gebrauch durch den Benutzer gedacht, sondern wird von der OnVistaApi verwendet. Der Übergang
# ist jedoch fließend, da die Response-Objekte der Low-Level-API auch die Response-Objekte der
# High-Level-API sind. ;-)
class OnVistaLowLevelApi:
    # Erzeugt eine neue Instanz der OnVistaLowLevelApi. Für jeden Benutzer sollte eine eigene Instanz
    # mit einem eigenen Cookie-File erzeugt werden. Das Cookie-File wird automatisch erstellt und fortgeschrieben
    # und ermöglicht das automatische Login ohne erneute Eingabe eines OTP (One-Time-Password).
    def __init__(self, cookies_file_name):
        self.session = req.Session()

        self.cookies_file_name = cookies_file_name
        try:
            cookies_file = open(cookies_file_name)

            with cookies_file:
                cookies = json.load(cookies_file)
                self.session.cookies = cookiejar_from_dict(cookies)

                log.debug(
                    f"Aus der Datei {cookies_file_name} wurden die Cookies {cookies} gelesen."
                )

        except IOError as e:
            log.debug(
                f"Von der Datei {cookies_file_name} konnten keine Dateien geladen werden: {e}"
            )
            return

    # Gibt die Informationen über die aktuelle Session zurück.
    #
    # Beispiel-Response 1:
    #
    # Der Benutzer ist bereits eingeloggt.
    #
    # {'s0': {'result': {'user': {'login': 'AB640023', 'managerId': False, 'accountActivated': True, 'passwordMustBeChanged': None, 'canForce': False, 'canAffect': False, 'canCashAdjust': False, 'hasToPassConditionsLayer': True, 'customerJourneyPwdMustBeChg': False}, 'otpInfo': {'hasPassedOtpRegistration': True, 'useStrongAuth': True, 'hasToPassOtp': False, 'otpCodeLength': 6}, '_meta': {'requestExecutionTime': 0.0026679039001464844}}}}
    #
    # Beispiel-Response 2:
    #
    # Der Benutzer ist nicht eingeloggt.
    #
    # {'s0': {'result': {'user': [], 'otpInfo': {'hasPassedOtpRegistration': False, 'useStrongAuth': False, 'hasToPassOtp': False, 'otpCodeLength': 6}, '_meta': {'requestExecutionTime': 0.0009322166442871094}}}}
    def session_auth_refresh(self):
        logger.info("Refresh session requested...")
        return self.low_level_request("Session_Auth", "refresh", {})

    # Diese Methode speichert die Cookies der HTTP-Session in der vorgegebenen Datei.
    def _save_cookies(self):
        with open(self.cookies_file_name, "w") as cookies_file:
            cookies_dict = self.session.cookies.get_dict()

            json.dump(cookies_dict, fp=cookies_file, indent=4)

            log.debug(
                f"In die Datei {self.cookies_file_name} wurden die Cookies {cookies_dict} geschrieben."
            )

    # Alle Requests an die OnVista-API werden über diese Methode abgewickelt. Sie fügt die notwendigen
    # Metadaten hinzu und gibt die Antwort der API zurück. Dabei wird nur das relevante result-Objekt
    # zurückgegeben.
    #
    # Jeder Request wird in eine Domäne (domain) gruppiert und hat einen Service-Namen (service). Die
    # Parameter (params) sind ein Dictionary, das die Parameter des Requests enthält.
    #
    # Beispiel-Domains:
    # - Session_Auth
    # - Session_Otp
    # - Bank_Account
    # - Trading_Position
    #
    # Beispiel-Services:
    # - login (in der Domain Session_Auth)
    # - refresh (in der Domain Session_Auth)
    # - generateOtp (in der Domain Session_Otp)
    # - checkOtp (in der Domain Session_Otp)
    # - getAccountsList (in der Domain Bank_Account)
    # - getPositions (in der Domain Trading_Position)
    def low_level_request(self, domain, service, params):
        new_params = {"action[s0][params][" + k + "]": v for (k, v) in params.items()}

        post_params = {
            "hash[timestamp]": "",
            # hash[nonce] ist statisch
            "hash[nonce]": "92f4fc28c06101778253aacf1df29e80",
            "hash[device]": "Mozilla",
            "hash[os]": "Win32",
            # hash[udid] ist statisch
            "hash[udid]": "1",
            # hash[key] auch statisch?
            "hash[key]": "JKEIMG1J1NIJ5619",
            # hash[signature] ist statisch
            "hash[signature]": "ODlhOGE1MDA5NzMyNWE4ZDhhODhhNmQ3NTM4NDAxYWMwNTg1M2M5Nw%3D%3D",
            "action[s0][domain]": domain,
            "action[s0][service]": service,
        }

        params = {"s0": f"{domain}.{service}"}
        data = {**post_params, **new_params}

        logger.debug(
            f"Request: https://webtrading.onvista-bank.de/services/api/ mit params={params} und data={data}"
        )

        result = self.session.post(
            f"https://webtrading.onvista-bank.de/services/api/",
            params=params,
            data=data,
            headers={"X-XSRF-TOKEN": self.session.cookies.get("XSRF-TOKEN")},
        )

        # Cookies sofort nach jedem Request abspeichern
        self._save_cookies()

        result_data = result.json()

        logger.debug(f"Response: {result_data}")

        if "error" in result_data:
            err = result_data["error"]
            logger.info(f"Error in Response: {err}")
            raise make_onvista_exception(err["code"], err["message"])

        if not "s0" in result_data:
            logger.info("s0 is missing in ressponse data")

        if "error" in result_data["s0"]:
            err = result_data["s0"]["error"]
            logger.info(f"Error in Response: {err}")
            raise make_onvista_exception(err["code"], err["message"])

        if not "result" in result_data["s0"]:
            logger.info("s0.result is missing in response data")

        return result_data["s0"]["result"]

    # Wird im Rahmen des OTP-Verfahrens ausgeführt. Nach dem unfruchtbaren login()-Aufruf muss das OTP
    # durch diese Methode generiert werden. Dann wird das OTP per SMS an das Handy des Benutzers gesendet.
    #
    # Beispiel-Response:
    #
    # {
    #     's0': {
    #         'result': {
    #             'success': True,
    #             '_meta': {
    #                 'requestExecutionTime': 0.37509799003601
    #             }
    #         }
    #     }
    # }
    def generateOTP(self):
        return self.low_level_request("Session_Otp", "generateOtp", {})

    # Wird im Rahmen des OTP-Verfahrens ausgeführt. Nach dem Aufruf von generateOTP() muss das OTP
    # durch diese Methode überprüft werden. Erst danach ist der Login erfolgreich.
    #
    # Beispiel-Response:
    #
    # {
    #     's0': {
    #         'result': {
    #             'success': True,
    #             '_meta': {
    #                 'requestExecutionTime': 0.097944974899292
    #             }
    #         }
    #     }
    # }
    def checkOTP(self, otpToken):
        return self.low_level_request("Session_Otp", "checkOtp", {"otpToken": otpToken})

    # Führt den Login im System mit dem übergbenen Benutzernamen und Passwort durch. Gegebenenfalls wird
    # ein OTP (One-Time-Password) angefordert. Ein solches Verfahren sendet eine SMS mit einem Code an
    # das Handy des Benutzers, der dann mit der Methode generateOTP() erzeugt und mit der Methode checkOTP()
    # überprüft werden muss. Erst danach ist der Login erfolgreich.
    #
    # Ist otpInfo.hasToPassOtp == True, dann muss ein OTP mit der Methode generateOTP() angefordert werden. Sodann
    # muss die erhaltene SMS mit der Methode checkOTP() überprüft werden. Erst danach ist der Login erfolgreich. Ein erneuter
    # Aufruf von login() ist nicht notwendig. ToDo: den letzten Satz überprüfen!
    #
    # Beispiel-Response 1:
    #
    # Der Benutzer ist noch nicht eingeloggt.
    #
    # {
    #     'user': {
    #         'login': 'AB640023',
    #         'managerId': False,
    #         'accountActivated': True,
    #         'passwordMustBeChanged': None,
    #         'canForce': False,
    #         'canAffect': False,
    #         'canCashAdjust': False
    #     },
    #     'otpInfo': {
    #         'hasPassedOtpRegistration': True,
    #         'useStrongAuth': True,
    #         'hasToPassOtp': True,
    #         'otpCodeLength': 6
    #     },
    #     '_meta': {
    #         'requestExecutionTime': 0.3096718788147
    #     }
    # }
    #
    # Beispiel-Response 2:
    #
    # Der Benutzer ist bereits eingeloggt.
    #
    # {'s0': {'result': {'user': {'login': 'AB640023', 'managerId': False, 'accountActivated': True, 'passwordMustBeChanged': None, 'canForce': False, 'canAffect': False, 'canCashAdjust': False, 'hasToPassConditionsLayer': True, 'customerJourneyPwdMustBeChg': False}, 'otpInfo': {'hasPassedOtpRegistration': True, 'useStrongAuth': True, 'hasToPassOtp': False, 'otpCodeLength': 6}, '_meta': {'requestExecutionTime': 0.10663986206054688}}}}
    def login(self, loginName, loginPassword):
        return self.low_level_request(
            "Session_Auth",
            "login",
            {
                "login": loginName,
                "password": loginPassword,
                "fakePassword": "",
                "mgrUserID": "",
                "token": "",
            },
        )

    # Gibt für einen eingeloggten Benutzer die Liste der Konten zurück, die diesem Benutzer zugeordnet sind.
    #
    # Beispiel-Response:
    #
    # {
    #     'accountsList': [
    #         {
    #             'rib': '00001 00001 00000370093 73',
    #             'accountKey': '70ece771d0d23b39c8eb5cae80b3d910',
    #             'accountNumber': '370093',
    #             'sapCashAccountNumber': '0370093041',
    #             'iban': 'DE29514108000370093041',
    #             'bic': 'BOURDEFFXXX',
    #             'name': '',
    #             'currency': 'EUR',
    #             'buyPower': 1164.65,
    #             'creditLimit': 0,
    #             'currentBalance': 1164.65,
    #             'pricingLabel': '5EUR-Festpreis',
    #             'isCFDAccount': False,
    #             'isCompanyAccount': False,
    #             'amountLimit': 10000,
    #             'accountType': 'ORD'
    #         }
    #     ],
    #     'defaultAccountKey': False,
    #     '_meta': {
    #         'requestExecutionTime': 0.31768083572388
    #     }
    # }
    def getAccounts(self):
        return self.low_level_request("Bank_Account", "getAccountsList", {})

    # Gibt für einen eingeloggten Benutzer die Liste der Positionen zu einem Konto zurück, die diesem Benutzer zugeordnet sind. Also letzendlich
    # die Liste der Aktien oder sonstiger Wertpapiere, die der Benutzer auf diesem Konto besitzt.
    #
    # Beispiel-Response:
    #
    # {
    #     'portfolio': {
    #         'positions': [
    #             {
    #                 'symbol': 'LU1681045370.XETR.EUR',
    #                 'quantity': 420,
    #                 'name': 'AMUNDI MSCI EMU',
    #                 'isin': 'LU1681045370',
    #                 'wkn': 'A2H58J',
    #                 'type': 'ETF',
    #                 'category': 'ETF',
    #                 'country': 49,
    #                 'lastValue': 75.12,
    #                 'buyingValue': 70.123456,
    #                 'totalValue': 27451.2,
    #                 'totalPerformance': 2098.8,
    #                 'performancePercentage': 8.2765432109877,
    #                 'actualValue': 29550,
    #                 'dailyTotalPerformance': -25.2,
    #                 'dailyPerformancePx': -0.085106382978723,
    #                 'last': 75.12,
    #                 'purPendQty': 0,
    #                 'salePendQty': 0,
    #                 'instrument': {
    #                     'symbol': 'LU1681045370.XETR.EUR',
    #                     'label': 'AMUNDI MSCI EMU',
    #                     'isin': 'LU1681045370',
    #                     'wkn': 'A2H58J',
    #                     'code2': 'CZ11',
    #                     'delay': 'D',
    #                     'variation': -0.00085106382978723,
    #                     'variation_value': 0,
    #                     'last': 75.12,
    #                     'currency': 'EUR',
    #                     'settle': 0,
    #                     'previousClose': 75.18,
    #                     'open': 75.12,
    #                     'high': 75.54,
    #                     'low': 74.98,
    #                     'totalVolume': 0,
    #                     'exchangeId': '4902',
    #                     'co': None,
    #                     'tradeDate': '2019-03-07 21:45:31',
    #                     'exchangeLabel': 'Frankfurt',
    #                     'code': 'FRA',
    #                     'country': '49',
    #                     'countryLabel': 'Allemagne',
    #                     'category': 'STK',
    #                     'categoryLabel': 'Aktie',
    #                     'market': '',
    #                     'marketLabel': '',
    #                     'instrumentType': 'Stock',
    #                     'isTradable': True,
    #                     'canTrade': True,
    #                     'isPourcentage': False,
    #                     'factor': 1,
    #                     'isFrankfurtLocal': False,
    #                     'code_oms': 'XETR',
    #                     'atosSymbol': 'LU1681045370.XETR.EUR'
    #                 },
    #                 'memo': '',
    #                 'plans': [
    #
    #                 ],
    #                 'blockedPositions': [
    #
    #                 ],
    #                 'isPourcentage': False
    #             }
    #         ],
    #         'total': {
    #             'buyValue': 27451.2,
    #             'actualValue': 29550,
    #             'totalPerformance': 2098.8,
    #             'performancePercentage': 8.2765432109877,
    #             'totalDailyPerformance': -25.2,
    #             'totalDailyPerformancePx': -0.085106382978723
    #         }
    #     },
    #     '_meta': {
    #         'requestExecutionTime': 0.37493419647217
    #     }
    # }
    def tradingPositions(self, accountKey):
        return self.low_level_request(
            "Trading_Position",
            "getPositions",
            {"accountKey": accountKey, "withMemos": 1},
        )
