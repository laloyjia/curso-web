import os
import urllib.parse
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime

# Importaciones para la nube y correo
import cloudinary
import cloudinary.uploader
from flask_mail import Mail, Message  # <--- IMPORTANTE: Nuevo cartero

app = Flask(__name__)

# ==========================================
# --- 🟢 ÁREA DE CLAVES (SECRETO) ---
# ==========================================

# 1. CLAVES DE CLOUDINARY (IMÁGENES)
CLOUDINARY_CLOUD_NAME = "deoprp7l7"
CLOUDINARY_API_KEY = "313623665287215"
CLOUDINARY_API_SECRET = "u1KdKT-9WMjiSBJaA6RbBA928rA"

# 2. CLAVE DE BASE DE DATOS (NEON)
NEON_DB_URL = "postgresql://neondb_owner:npg_XZK5gAI0WNvh@ep-silent-union-a4u8ra5u-pooler.us-east-1.aws.neon.tech/neondb?sslmode=require"

# 3. CLAVES DE CORREO (GMAIL)
# ¡¡¡PEGA AQUÍ TU CLAVE DE 16 LETRAS QUE TE DIO GOOGLE!!! 👇
GMAIL_APP_PASSWORD = "uduc yeyy tatb yckq" 
GMAIL_USER = "chechidominguezr@gmail.com"

# ==========================================
# --- FIN ÁREA DE CLAVES -------------------
# ==========================================

# Configuración de Flask
app.config['SECRET_KEY'] = 'limalimoon_clave_super_secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = NEON_DB_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuración de Correo (Flask-Mail)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = GMAIL_USER
app.config['MAIL_PASSWORD'] = GMAIL_APP_PASSWORD

# Inicialización
db = SQLAlchemy(app)
mail = Mail(app)  # <--- Iniciamos el servicio de correo
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Inicia sesión para comprar."

# --- MODELOS ---

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))
    apellido = db.Column(db.String(100))
    direccion = db.Column(db.String(200))
    telefono = db.Column(db.String(20))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(200))
    is_admin = db.Column(db.Boolean, default=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, default=0)
    image = db.Column(db.String(300))
    category = db.Column(db.String(50))
    description = db.Column(db.Text)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    total_price = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='Pendiente')
    date_ordered = db.Column(db.DateTime, default=datetime.utcnow)
    details = db.relationship('OrderDetail', backref='order', lazy=True)

class OrderDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_name = db.Column(db.String(100))
    product_price = db.Column(db.Integer)
    quantity = db.Column(db.Integer)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    product = db.relationship('Product')

# --- CONFIGURACIÓN CLOUDINARY ---
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET
)

# --- CARGADORES ---

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('⛔ Acceso exclusivo administradores.', 'error')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        items = CartItem.query.filter_by(user_id=current_user.id).all()
        count = sum(item.quantity for item in items if item.product)
    else:
        count = 0
    return dict(cart_count=count)

# --- RUTAS PÚBLICAS ---

@app.route('/')
def home():
    products = Product.query.all()
    return render_template('index.html', products=products)

@app.route('/carrito')
@login_required
def carrito():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    # Limpieza básica
    for item in cart_items:
        if not item.product:
            db.session.delete(item)
    db.session.commit()

    # Recálculo
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.product.price * item.quantity for item in cart_items if item.product)
    costo_envio = 0 if subtotal > 25000 else 3500
    total_final = subtotal + costo_envio
    
    return render_template('cart.html', cart_items=cart_items, subtotal=subtotal, costo_envio=costo_envio, total=total_final)

@app.route('/add_to_cart/<int:product_id>')
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)
    if product.stock <= 0:
        flash('Producto agotado.', 'error')
        return redirect(request.referrer or url_for('home'))

    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        if item.quantity < product.stock:
            item.quantity += 1
            flash('Cantidad actualizada.', 'info')
        else:
            flash('Stock máximo alcanzado.', 'warning')
    else:
        db.session.add(CartItem(user_id=current_user.id, product_id=product_id, quantity=1))
        flash('Agregado al carrito.', 'success')
        
    db.session.commit()
    return redirect(request.referrer or url_for('home'))

@app.route('/update_cart/<int:product_id>/<action>')
@login_required
def update_cart(product_id, action):
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item and item.product:
        if action == 'increase':
            if item.quantity < item.product.stock:
                item.quantity += 1
        elif action == 'decrease':
            item.quantity -= 1
        
        if item.quantity <= 0:
            db.session.delete(item)
        db.session.commit()
    return redirect(url_for('carrito'))

@app.route('/remove_from_cart/<int:product_id>')
@login_required
def remove_from_cart(product_id):
    item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    return redirect(url_for('carrito'))

@app.route('/confirmar_pedido', methods=['POST'])
@login_required
def confirmar_pedido():
    try:
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        if not cart_items: return redirect(url_for('home'))

        subtotal = 0
        items_msg = []
        direccion = request.form.get('direccion') or current_user.direccion or "Por coordinar"

        for item in cart_items:
            if not item.product: continue
            total_linea = item.product.price * item.quantity
            subtotal += total_linea
            items_msg.append({'cant': item.quantity, 'nombre': item.product.name, 'precio': total_linea})

        costo_envio = 0 if subtotal > 25000 else 3500
        total_final = subtotal + costo_envio

        new_order = Order(user_id=current_user.id, total_price=total_final, status='Pendiente')
        db.session.add(new_order)
        db.session.commit()

        for item in cart_items:
            if item.product:
                item.product.stock -= item.quantity
                detail = OrderDetail(
                    order_id=new_order.id, 
                    product_name=item.product.name, 
                    product_price=item.product.price, 
                    quantity=item.quantity
                )
                db.session.add(detail)
                db.session.delete(item)
        
        db.session.commit()

        msg = f"Hola LimaLimoon! 🍋 Nuevo pedido de *{current_user.nombre}*:\n\n"
        for i in items_msg:
            msg += f"- {i['cant']}x {i['nombre']} (${'{:,.0f}'.format(i['precio']).replace(',','.')})\n"
        
        msg += f"\n💰 *Total: ${'{:,.0f}'.format(total_final).replace(',','.')}*"
        msg += f"\n📍 Dirección: {direccion}"
        msg += f"\n🧾 Orden #{new_order.id}"
        
        whatsapp_url = f"https://wa.me/56968498218?text={urllib.parse.quote(msg)}"
        return redirect(whatsapp_url)

    except Exception as e:
        db.session.rollback()
        print(f"Error: {e}")
        flash('Error al procesar el pedido.', 'error')
        return redirect(url_for('carrito'))

# --- AUTH Y REGISTRO (AQUÍ ESTÁ LA MAGIA DEL CORREO) ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form['email'].lower().strip()
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or (url_for('admin_dashboard') if user.is_admin else url_for('home')))
        flash('Credenciales incorrectas.', 'error')
    return render_template('auth/login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated: return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form.get('email').lower().strip()
        if User.query.filter_by(email=email).first():
            flash('Email ya registrado.', 'error')
        else:
            # 1. Crear Usuario
            nombre = request.form.get('nombre')
            apellido = request.form.get('apellido')
            telefono = request.form.get('telefono')
            
            new_user = User(
                nombre=nombre, 
                apellido=apellido,
                direccion=request.form.get('direccion'), 
                telefono=telefono,
                email=email, 
                password=generate_password_hash(request.form.get('password')),
                is_admin=False
            )
            db.session.add(new_user)
            db.session.commit()
            
            # 2. ENVIAR CORREO DE ALERTA AL ADMIN (TÚ) 📧
            try:
                msg = Message(
                    subject="🔔 Nuevo Cliente en LimaLimoon",
                    sender=app.config['MAIL_USERNAME'],
                    recipients=[app.config['MAIL_USERNAME']], # Te lo envías a ti misma
                    body=f"""
                    ¡Hola Chechi!

                    Alguien nuevo se ha registrado en la tienda:
                    
                    👤 Nombre: {nombre} {apellido}
                    📧 Email: {email}
                    📞 Teléfono: {telefono}
                    
                    Revisa el panel de control para más detalles.
                    """
                )
                mail.send(msg)
                print(">>> Correo de alerta enviado exitosamente.")
            except Exception as e:
                print(f"Error enviando correo: {e}")
                # No detenemos el registro si falla el correo, solo lo imprimimos
            
            flash('Cuenta creada. Inicia sesión.', 'success')
            return redirect(url_for('login'))
            
    return render_template('auth/register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/perfil')
@login_required
def perfil():
    mis_ordenes = Order.query.filter_by(user_id=current_user.id).order_by(Order.date_ordered.desc()).all()
    return render_template('perfil.html', user=current_user, orders=mis_ordenes)

@app.route('/editar_perfil', methods=['GET', 'POST'])
@login_required
def editar_perfil():
    if request.method == 'POST':
        current_user.nombre = request.form.get('nombre')
        current_user.apellido = request.form.get('apellido')
        current_user.telefono = request.form.get('telefono')
        current_user.direccion = request.form.get('direccion')
        db.session.commit()
        return redirect(url_for('perfil'))
    return render_template('editar_perfil.html')

# --- ADMIN DASHBOARD CON ESTADÍSTICAS ---

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    # 1. Calcular Dinero Total (Solo de ventas NO canceladas)
    ventas_validas = Order.query.filter(Order.status != 'Cancelada').all()
    total_dinero = sum(o.total_price for o in ventas_validas)

    # 2. Contar Pedidos Pendientes
    pendientes = Order.query.filter_by(status='Pendiente').count()

    # 3. Alerta de Stock Bajo (Menos de 5 unidades)
    low_stock = Product.query.filter(Product.stock <= 5).count()

    # 4. Cantidad de Clientes (excluyendo al admin)
    clientes = User.query.filter(User.is_admin == False).count()

    return render_template('admin_dashboard.html', 
                         total_dinero=total_dinero, 
                         pendientes=pendientes, 
                         low_stock=low_stock,
                         clientes=clientes)

@app.route('/admin/usuarios')
@login_required
@admin_required
def lista_usuarios():
    return render_template('admin_usuarios.html', usuarios=User.query.all())
@app.route('/admin/usuario/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_usuario(id):
    user = User.query.get_or_404(id)
    
    # 1. PROTECCIÓN: No te puedes borrar a ti misma
    if user.id == current_user.id:
        flash('⛔ ¡No puedes eliminar tu propia cuenta de administrador!', 'error')
        return redirect(url_for('lista_usuarios'))
    
    # 2. PROTECCIÓN: No borrar si tiene compras (Historial de ventas)
    # Buscamos si este usuario tiene alguna orden asociada
    ordenes_usuario = Order.query.filter_by(user_id=id).first()
    
    if ordenes_usuario:
        flash('⚠️ No se puede eliminar: Este usuario tiene historial de compras. Borrarlo afectaría tus reportes de venta.', 'warning')
        return redirect(url_for('lista_usuarios'))

    try:
        # 3. Limpiar carrito del usuario antes de borrar (para que no de error)
        CartItem.query.filter_by(user_id=id).delete()
        
        # 4. Borrar usuario
        db.session.delete(user)
        db.session.commit()
        flash(f'Usuario {user.nombre} eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar: {str(e)}', 'error')

    return redirect(url_for('lista_usuarios'))
@app.route('/admin/productos', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_productos():
    if request.method == 'POST':
        try:
            name = request.form.get('name')
            price = float(request.form.get('price'))
            stock = int(request.form.get('stock'))
            description = request.form.get('description')
            category = request.form.get('category')
            
            image_url = "https://via.placeholder.com/150"
            f = request.files.get('image')
            
            if f and f.filename != '':
                upload_result = cloudinary.uploader.upload(f)
                image_url = upload_result['secure_url']
            
            new_prod = Product(
                name=name, price=price, stock=stock, 
                image=image_url,
                description=description, category=category
            )
            db.session.add(new_prod)
            db.session.commit()
            flash('Producto creado con éxito en la Nube.', 'success')
        except Exception as e:
            flash(f'Error: {e}', 'error')
            
        return redirect(url_for('admin_productos'))
        
    return render_template('admin_products.html', products=Product.query.order_by(Product.id.desc()).all())

@app.route('/admin/producto/editar/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def editar_producto(id):
    p = Product.query.get_or_404(id)
    if request.method == 'POST':
        p.name = request.form.get('name')
        p.stock = int(request.form.get('stock'))
        p.price = float(request.form.get('price'))
        p.description = request.form.get('description')
        p.category = request.form.get('category')
        
        f = request.files.get('image')
        if f and f.filename != '':
            upload_result = cloudinary.uploader.upload(f)
            p.image = upload_result['secure_url']
            
        db.session.commit()
        flash('Producto actualizado.', 'success')
        return redirect(url_for('admin_productos'))
        
    return render_template('admin_product_edit.html', product=p)

@app.route('/admin/producto/eliminar/<int:id>')
@login_required
@admin_required
def eliminar_producto(id):
    try:
        p = Product.query.get_or_404(id)
        db.session.delete(p)
        db.session.commit()
        flash('Producto eliminado.', 'success')
    except:
        flash('No se puede eliminar (tiene pedidos asociados).', 'error')
    return redirect(url_for('admin_productos'))

@app.route('/admin/stock')
@login_required
@admin_required
def admin_stock():
    products = Product.query.order_by(Product.name).all()
    return render_template('admin_stock.html', products=products)

@app.route('/admin/stock/update/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def update_stock(product_id):
    p = Product.query.get_or_404(product_id)
    new_stock = request.form.get('new_stock')
    
    if new_stock:
        try:
            p.stock = int(new_stock)
            db.session.commit()
            flash(f'Stock actualizado para: {p.name}', 'success')
        except ValueError:
            flash('Error: Ingresa un número válido.', 'error')
            
    return redirect(url_for('admin_stock'))

@app.route('/admin/ordenes')
@login_required
@admin_required
def admin_ordenes():
    orders = Order.query.order_by(Order.date_ordered.desc()).all()
    return render_template('admin_orders.html', orders=orders)

@app.route('/admin/orden/<int:order_id>/<action>')
@login_required
@admin_required
def gestionar_orden_estado(order_id, action):
    order = Order.query.get_or_404(order_id)
    
    if action == 'completar':
        order.status = 'Completada'
        flash(f'Orden #{order.id} marcada como COMPLETADA.', 'success')

    elif action == 'cancelar':
        if order.status != 'Cancelada':
            print(f"Cancelando orden #{order.id} y devolviendo stock...")
            for detalle in order.details:
                producto_original = Product.query.filter_by(name=detalle.product_name).first()
                if producto_original:
                    producto_original.stock += detalle.quantity
            order.status = 'Cancelada'
            flash(f'Orden #{order.id} CANCELADA. Stock restaurado.', 'warning')
        else:
            flash('Esta orden ya estaba cancelada.', 'info')

    db.session.commit()
    return redirect(url_for('admin_ordenes'))

# --- HERRAMIENTAS DB ---

@app.route('/db-setup')
def db_setup():
    try:
        with app.app_context():
            db.create_all()
        return "<h1>✅ Tablas actualizadas.</h1>"
    except Exception as e:
        return f"<h1>❌ Error: {e}</h1>"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Admin automático
        if not User.query.filter_by(email='admin@limalimoon.cl').first():
            print(">>> Creando Admin en Neon...")
            admin = User(
                nombre='Admin', apellido='Sistema', 
                email='admin@limalimoon.cl', 
                password=generate_password_hash('admin123'), 
                is_admin=True
            )
            db.session.add(admin)
            db.session.commit()
    
    app.run(debug=True)

