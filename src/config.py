import configparser


# Liest die secrets.properties Datei und gibt ein ConfigParser-Objekt zurück.
def read_secrets():
    config = configparser.ConfigParser()
    config.read("secrets.properties")

    return config


# Gibt den OnVistaBank-Benutzernamen aus der secrets.properties Datei zurück.
def get_onvistabank_username():
    config = read_secrets()
    username = config.get("secrets", "ONVISTABANK_USERNAME")
    return username


# Gibt das OnVistaBank-Passwort aus der secrets.properties Datei zurück.
def get_onvistabank_password():
    config = read_secrets()
    password = config.get("secrets", "ONVISTABANK_PASSWORD")
    return password


# Gibt das Telegram-API-Token aus der secrets.properties Datei zurück.
def get_telegram_token():
    config = read_secrets()
    token = config.get("secrets", "TELEGRAM_API_TOKEN")
    return token


# Gibt die Benutzer-IDs zurück, die Nachrichten erhalten dürfen. Diese sind
# in der secrets.properties Datei definiert. Gibt eine Liste von Strings zurück.
def get_allowed_user_ids():
    config = read_secrets()
    allowed_user_ids = config.get("secrets", "ALLOWED_USER_IDS")
    return allowed_user_ids.split(",")
