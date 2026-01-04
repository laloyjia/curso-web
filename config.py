import os

class Config:
    # Clave secreta para proteger las sesiones y cookies
    SECRET_KEY = 'lumiere_clave_secreta_super_segura' 
    
    # Configuración de la base de datos (se creará un archivo local sqlite)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///lumiere.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False