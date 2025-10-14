from werkzeug.security import check_password_hash
from flask_login import UserMixin

class User(UserMixin):
    def __init__(self, id_usuario, correo_electronico, contraseña, nombre_completo="", id_rol=None):
        self.id = id_usuario
        self.correo_electronico = correo_electronico
        self.contraseña = contraseña
        self.nombre_completo = nombre_completo
        self.id_rol = id_rol   # 👈 aquí agregamos el rol
    
    @classmethod
    def check_password(cls, hashed_password, password):
        return check_password_hash(hashed_password, password)
