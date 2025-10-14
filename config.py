class Config:
    SECRET_KEY = 'your_secret_key'

    # Configuración de correo con Gmail
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = "pipeg5275@gmail.com"
    MAIL_PASSWORD = "nmeqvujhvrtyeqzn"
    MAIL_DEFAULT_SENDER = ("HandiGenius", "pipeg5275@gmail.com")


class DevelopmentConfig(Config):
    DEBUG = True
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = ''
    MYSQL_DB = 'handigeniussandra'


config = {
    'development': DevelopmentConfig
}
