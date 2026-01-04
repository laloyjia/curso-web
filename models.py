from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

db = SQLAlchemy()

# Tabla de Usuarios
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    apellido = db.Column(db.String(100))
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    
    # Datos de perfil
    telefono = db.Column(db.String(20))
    direccion = db.Column(db.String(200))
    sexo = db.Column(db.String(20)) # Opcional, si lo usas en el registro
    
    is_admin = db.Column(db.Boolean, default=False)

# Tabla de Productos
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False) # Usamos Float, pero recuerda que en CLP no usamos decimales.
    image = db.Column(db.String(100), nullable=False, default='default.jpg')
    description = db.Column(db.Text)
    stock = db.Column(db.Integer, default=0)
    category = db.Column(db.String(50))

# Tabla de Pedidos (Ordenes - Historial)
class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # utcnow guarda la hora universal. En Chile son -3 o -4 horas.
    date_ordered = db.Column(db.DateTime, default=datetime.utcnow) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    total_price = db.Column(db.Float) 
    status = db.Column(db.String(50), default='Pendiente') # Pendiente, Pagado, Enviado
    
    # Relación con Detalles
    details = db.relationship('OrderDetail', backref='order', lazy=True)

# Tabla de Detalles del Pedido (Historial Estático)
class OrderDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    
    # IMPORTANTE: Guardamos el nombre y precio COMO TEXTO/VALOR.
    # Si borras el producto original o cambias su precio, este historial NO cambia.
    product_name = db.Column(db.String(100))
    product_price = db.Column(db.Float)
    quantity = db.Column(db.Integer)

# Tabla del Carrito de Compras (Temporal)
class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    
    # Relaciones
    user = db.relationship('User', backref=db.backref('cart_items', lazy=True))
    product = db.relationship('Product', backref=db.backref('cart_items', lazy=True))