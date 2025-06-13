from flask import Flask, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import re

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'tu_clave_secreta_para_desarrollo')

# Detectar si estamos en producción (Render) o desarrollo
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db_connection():
    if DATABASE_URL:
        # Producción - PostgreSQL
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    else:
        # Desarrollo - SQLite
        conn = sqlite3.connect('contactos.db')
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    """Inicializar la base de datos - se ejecuta automáticamente"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            # PostgreSQL - Crear tabla de usuarios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    nombre_completo VARCHAR(100) NOT NULL,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activo BOOLEAN DEFAULT TRUE
                )
            ''')
            
            # PostgreSQL - Crear tabla de contactos con FK a usuarios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contactos (
                    id SERIAL PRIMARY KEY,
                    usuario_id INTEGER NOT NULL,
                    nombre VARCHAR(100) NOT NULL,
                    telefono VARCHAR(20) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    categoria VARCHAR(50) DEFAULT 'General',
                    notas TEXT,
                    favorito BOOLEAN DEFAULT FALSE,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
                )
            ''')
            
            # Crear índices para mejor performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_contactos_usuario ON contactos(usuario_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_contactos_nombre ON contactos(nombre)')
            
        else:
            # SQLite - Crear tabla de usuarios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS usuarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    nombre_completo TEXT NOT NULL,
                    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    activo INTEGER DEFAULT 1
                )
            ''')
            
            # SQLite - Crear tabla de contactos con FK a usuarios
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contactos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    usuario_id INTEGER NOT NULL,
                    nombre TEXT NOT NULL,
                    telefono TEXT NOT NULL,
                    email TEXT NOT NULL,
                    categoria TEXT DEFAULT 'General',
                    notas TEXT,
                    favorito INTEGER DEFAULT 0,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    fecha_modificacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (usuario_id) REFERENCES usuarios (id) ON DELETE CASCADE
                )
            ''')
        
        conn.commit()
        conn.close()
        print("Base de datos inicializada correctamente")
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")

# Decorador para requerir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Debes iniciar sesión para acceder a esta página', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Funciones de validación
def validar_email(email):
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None

def validar_username(username):
    # Solo letras, números y guiones bajos, entre 3 y 20 caracteres
    patron = r'^[a-zA-Z0-9_]{3,20}$'
    return re.match(patron, username) is not None

def validar_password(password):
    # Al menos 6 caracteres, una letra y un número
    return len(password) >= 6 and any(c.isalpha() for c in password) and any(c.isdigit() for c in password)

# Inicializar DB
init_db()

# ==================== RUTAS DE AUTENTICACIÓN ====================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        password_confirm = request.form['password_confirm']
        nombre_completo = request.form['nombre_completo'].strip()
        
        # Validaciones
        if not all([username, email, password, nombre_completo]):
            flash('Todos los campos son obligatorios', 'error')
            return render_template('register.html')
        
        if not validar_username(username):
            flash('El username debe tener entre 3-20 caracteres y solo letras, números y guiones bajos', 'error')
            return render_template('register.html')
        
        if not validar_email(email):
            flash('Por favor ingresa un email válido', 'error')
            return render_template('register.html')
        
        if not validar_password(password):
            flash('La contraseña debe tener al menos 6 caracteres, incluyendo letras y números', 'error')
            return render_template('register.html')
        
        if password != password_confirm:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('register.html')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Verificar si ya existe el usuario o email
            if DATABASE_URL:
                cursor.execute('SELECT id FROM usuarios WHERE username = %s OR email = %s', (username, email))
            else:
                cursor.execute('SELECT id FROM usuarios WHERE username = ? OR email = ?', (username, email))
            
            if cursor.fetchone():
                flash('El username o email ya están registrados', 'error')
                conn.close()
                return render_template('register.html')
            
            # Crear nuevo usuario
            password_hash = generate_password_hash(password)
            
            if DATABASE_URL:
                cursor.execute('''
                    INSERT INTO usuarios (username, email, password_hash, nombre_completo) 
                    VALUES (%s, %s, %s, %s)
                ''', (username, email, password_hash, nombre_completo))
            else:
                cursor.execute('''
                    INSERT INTO usuarios (username, email, password_hash, nombre_completo) 
                    VALUES (?, ?, ?, ?)
                ''', (username, email, password_hash, nombre_completo))
            
            conn.commit()
            conn.close()
            
            flash('¡Registro exitoso! Ya puedes iniciar sesión', 'success')
            return redirect(url_for('login'))
            
        except Exception as e:
            flash('Error al registrar usuario. Intenta nuevamente.', 'error')
            print(f"Error en registro: {e}")
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower()
        password = request.form['password']
        
        if not username or not password:
            flash('Por favor completa todos los campos', 'error')
            return render_template('login.html')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if DATABASE_URL:
                cursor.execute('SELECT * FROM usuarios WHERE username = %s AND activo = TRUE', (username,))
            else:
                cursor.execute('SELECT * FROM usuarios WHERE username = ? AND activo = 1', (username,))
            
            usuario = cursor.fetchone()
            conn.close()
            
            if usuario and check_password_hash(usuario['password_hash'], password):
                session['user_id'] = usuario['id']
                session['username'] = usuario['username']
                session['nombre_completo'] = usuario['nombre_completo']
                flash(f'¡Bienvenido/a {usuario["nombre_completo"]}!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Username o contraseña incorrectos', 'error')
                
        except Exception as e:
            flash('Error al iniciar sesión. Intenta nuevamente.', 'error')
            print(f"Error en login: {e}")
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    nombre = session.get('nombre_completo', 'Usuario')
    session.clear()
    flash(f'¡Hasta luego {nombre}!', 'success')
    return redirect(url_for('login'))

# ==================== RUTAS PRINCIPALES ====================

@app.route('/')
@login_required
def index():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            cursor.execute('''
                SELECT * FROM contactos 
                WHERE usuario_id = %s 
                ORDER BY favorito DESC, nombre ASC
            ''', (session['user_id'],))
        else:
            cursor.execute('''
                SELECT * FROM contactos 
                WHERE usuario_id = ? 
                ORDER BY favorito DESC, nombre ASC
            ''', (session['user_id'],))
        
        contactos = cursor.fetchall()
        conn.close()
        
        return render_template('index.html', contactos=contactos)
    except Exception as e:
        flash('Error al cargar contactos', 'error')
        print(f"Error en index: {e}")
        return render_template('index.html', contactos=[])

@app.route('/agregar', methods=['GET', 'POST'])
@login_required
def agregar_contacto():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        telefono = request.form['telefono'].strip()
        email = request.form['email'].strip()
        categoria = request.form.get('categoria', 'General').strip()
        notas = request.form.get('notas', '').strip()
        favorito = 'favorito' in request.form
        
        if not all([nombre, telefono, email]):
            flash('Nombre, teléfono y email son obligatorios', 'error')
            return render_template('agregar.html')
        
        if not validar_email(email):
            flash('Por favor ingresa un email válido', 'error')
            return render_template('agregar.html')
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            if DATABASE_URL:
                cursor.execute('''
                    INSERT INTO contactos (usuario_id, nombre, telefono, email, categoria, notas, favorito) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (session['user_id'], nombre, telefono, email, categoria, notas, favorito))
            else:
                cursor.execute('''
                    INSERT INTO contactos (usuario_id, nombre, telefono, email, categoria, notas, favorito) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (session['user_id'], nombre, telefono, email, categoria, notas, favorito))
            
            conn.commit()
            conn.close()
            flash('¡Contacto agregado exitosamente!', 'success')
            return redirect(url_for('index'))
            
        except Exception as e:
            flash('Error al agregar contacto. Intenta nuevamente.', 'error')
            print(f"Error al agregar contacto: {e}")
    
    return render_template('agregar.html')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_contacto(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Verificar que el contacto pertenece al usuario actual
        if DATABASE_URL:
            cursor.execute('SELECT * FROM contactos WHERE id = %s AND usuario_id = %s', (id, session['user_id']))
        else:
            cursor.execute('SELECT * FROM contactos WHERE id = ? AND usuario_id = ?', (id, session['user_id']))
        
        contacto = cursor.fetchone()
        
        if not contacto:
            flash('Contacto no encontrado', 'error')
            conn.close()
            return redirect(url_for('index'))
        
        if request.method == 'POST':
            nombre = request.form['nombre'].strip()
            telefono = request.form['telefono'].strip()
            email = request.form['email'].strip()
            categoria = request.form.get('categoria', 'General').strip()
            notas = request.form.get('notas', '').strip()
            favorito = 'favorito' in request.form
            
            if not all([nombre, telefono, email]):
                flash('Nombre, teléfono y email son obligatorios', 'error')
                return render_template('editar.html', contacto=contacto)
            
            if not validar_email(email):
                flash('Por favor ingresa un email válido', 'error')
                return render_template('editar.html', contacto=contacto)
            
            if DATABASE_URL:
                cursor.execute('''
                    UPDATE contactos 
                    SET nombre = %s, telefono = %s, email = %s, categoria = %s, 
                        notas = %s, favorito = %s, fecha_modificacion = CURRENT_TIMESTAMP
                    WHERE id = %s AND usuario_id = %s
                ''', (nombre, telefono, email, categoria, notas, favorito, id, session['user_id']))
            else:
                cursor.execute('''
                    UPDATE contactos 
                    SET nombre = ?, telefono = ?, email = ?, categoria = ?, 
                        notas = ?, favorito = ?, fecha_modificacion = CURRENT_TIMESTAMP
                    WHERE id = ? AND usuario_id = ?
                ''', (nombre, telefono, email, categoria, notas, favorito, id, session['user_id']))
            
            conn.commit()
            conn.close()
            flash('¡Contacto actualizado exitosamente!', 'success')
            return redirect(url_for('index'))
        
        conn.close()
        return render_template('editar.html', contacto=contacto)
        
    except Exception as e:
        flash('Error al editar contacto', 'error')
        print(f"Error al editar contacto: {e}")
        return redirect(url_for('index'))

@app.route('/eliminar/<int:id>')
@login_required
def eliminar_contacto(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            cursor.execute('DELETE FROM contactos WHERE id = %s AND usuario_id = %s', (id, session['user_id']))
        else:
            cursor.execute('DELETE FROM contactos WHERE id = ? AND usuario_id = ?', (id, session['user_id']))
        
        if cursor.rowcount > 0:
            flash('¡Contacto eliminado exitosamente!', 'success')
        else:
            flash('Contacto no encontrado', 'error')
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        flash('Error al eliminar contacto', 'error')
        print(f"Error al eliminar contacto: {e}")
    
    return redirect(url_for('index'))

@app.route('/buscar', methods=['GET', 'POST'])
@login_required
def buscar_contacto():
    contactos = []
    if request.method == 'POST':
        busqueda = request.form['busqueda'].strip()
        if busqueda:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                if DATABASE_URL:
                    cursor.execute('''
                        SELECT * FROM contactos 
                        WHERE usuario_id = %s AND (
                            nombre ILIKE %s OR telefono ILIKE %s OR 
                            email ILIKE %s OR categoria ILIKE %s
                        )
                        ORDER BY favorito DESC, nombre ASC
                    ''', (session['user_id'], f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%'))
                else:
                    cursor.execute('''
                        SELECT * FROM contactos 
                        WHERE usuario_id = ? AND (
                            nombre LIKE ? OR telefono LIKE ? OR 
                            email LIKE ? OR categoria LIKE ?
                        )
                        ORDER BY favorito DESC, nombre ASC
                    ''', (session['user_id'], f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%'))
                
                contactos = cursor.fetchall()
                conn.close()
                
            except Exception as e:
                flash('Error en la búsqueda. Intenta nuevamente.', 'error')
                print(f"Error en búsqueda: {e}")
    
    return render_template('buscar.html', contactos=contactos)

@app.route('/perfil')
@login_required
def perfil():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Obtener estadísticas del usuario
        if DATABASE_URL:
            cursor.execute('SELECT COUNT(*) as total FROM contactos WHERE usuario_id = %s', (session['user_id'],))
            total_contactos = cursor.fetchone()['total']
            
            cursor.execute('SELECT COUNT(*) as favoritos FROM contactos WHERE usuario_id = %s AND favorito = TRUE', (session['user_id'],))
            total_favoritos = cursor.fetchone()['favoritos']
            
            cursor.execute('''
                SELECT categoria, COUNT(*) as cantidad 
                FROM contactos 
                WHERE usuario_id = %s 
                GROUP BY categoria 
                ORDER BY cantidad DESC
            ''', (session['user_id'],))
        else:
            cursor.execute('SELECT COUNT(*) as total FROM contactos WHERE usuario_id = ?', (session['user_id'],))
            total_contactos = cursor.fetchone()['total']
            
            cursor.execute('SELECT COUNT(*) as favoritos FROM contactos WHERE usuario_id = ? AND favorito = 1', (session['user_id'],))
            total_favoritos = cursor.fetchone()['favoritos']
            
            cursor.execute('''
                SELECT categoria, COUNT(*) as cantidad 
                FROM contactos 
                WHERE usuario_id = ? 
                GROUP BY categoria 
                ORDER BY cantidad DESC
            ''', (session['user_id'],))
        
        categorias = cursor.fetchall()
        conn.close()
        
        return render_template('perfil.html', 
                             total_contactos=total_contactos, 
                             total_favoritos=total_favoritos,
                             categorias=categorias)
    except Exception as e:
        flash('Error al cargar perfil', 'error')
        print(f"Error en perfil: {e}")
        return redirect(url_for('index'))

# Para desarrollo local
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))