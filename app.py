from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os
import psycopg2
from psycopg2.extras import RealDictCursor

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
            # PostgreSQL
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contactos (
                    id SERIAL PRIMARY KEY,
                    nombre VARCHAR(100) NOT NULL,
                    telefono VARCHAR(20) NOT NULL,
                    email VARCHAR(100) NOT NULL,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        else:
            # SQLite
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS contactos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre TEXT NOT NULL,
                    telefono TEXT NOT NULL,
                    email TEXT NOT NULL,
                    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        conn.commit()
        conn.close()
        print("Base de datos inicializada correctamente")
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")

# IMPORTANTE: Inicializar la base de datos al importar el módulo
# Esto asegura que se ejecute tanto en desarrollo como en producción
init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM contactos ORDER BY nombre')
    contactos = cursor.fetchall()
    conn.close()
    return render_template('index.html', contactos=contactos)

@app.route('/agregar', methods=['GET', 'POST'])
def agregar_contacto():
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        telefono = request.form['telefono'].strip()
        email = request.form['email'].strip()
        
        if nombre and telefono and email:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute(
                    'INSERT INTO contactos (nombre, telefono, email) VALUES (%s, %s, %s)' if DATABASE_URL 
                    else 'INSERT INTO contactos (nombre, telefono, email) VALUES (?, ?, ?)',
                    (nombre, telefono, email)
                )
                conn.commit()
                conn.close()
                flash('Contacto agregado exitosamente!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash('Error al agregar contacto. Intenta nuevamente.', 'error')
                print(f"Error al agregar contacto: {e}")
        else:
            flash('Por favor completa todos los campos', 'error')
    
    return render_template('agregar.html')

@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_contacto(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if DATABASE_URL:
        cursor.execute('SELECT * FROM contactos WHERE id = %s', (id,))
    else:
        cursor.execute('SELECT * FROM contactos WHERE id = ?', (id,))
    
    contacto = cursor.fetchone()
    
    if request.method == 'POST':
        nombre = request.form['nombre'].strip()
        telefono = request.form['telefono'].strip()
        email = request.form['email'].strip()
        
        if nombre and telefono and email:
            try:
                if DATABASE_URL:
                    cursor.execute(
                        'UPDATE contactos SET nombre = %s, telefono = %s, email = %s WHERE id = %s',
                        (nombre, telefono, email, id)
                    )
                else:
                    cursor.execute(
                        'UPDATE contactos SET nombre = ?, telefono = ?, email = ? WHERE id = ?',
                        (nombre, telefono, email, id)
                    )
                conn.commit()
                conn.close()
                flash('Contacto actualizado exitosamente!', 'success')
                return redirect(url_for('index'))
            except Exception as e:
                flash('Error al actualizar contacto. Intenta nuevamente.', 'error')
                print(f"Error al actualizar contacto: {e}")
        else:
            flash('Por favor completa todos los campos', 'error')
    
    conn.close()
    return render_template('editar.html', contacto=contacto)

@app.route('/eliminar/<int:id>')
def eliminar_contacto(id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if DATABASE_URL:
            cursor.execute('DELETE FROM contactos WHERE id = %s', (id,))
        else:
            cursor.execute('DELETE FROM contactos WHERE id = ?', (id,))
        
        conn.commit()
        conn.close()
        flash('Contacto eliminado exitosamente!', 'success')
    except Exception as e:
        flash('Error al eliminar contacto. Intenta nuevamente.', 'error')
        print(f"Error al eliminar contacto: {e}")
    
    return redirect(url_for('index'))

@app.route('/buscar', methods=['GET', 'POST'])
def buscar_contacto():
    contactos = []
    if request.method == 'POST':
        busqueda = request.form['busqueda'].strip()
        if busqueda:
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                if DATABASE_URL:
                    cursor.execute(
                        'SELECT * FROM contactos WHERE nombre ILIKE %s OR telefono ILIKE %s OR email ILIKE %s',
                        (f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%')
                    )
                else:
                    cursor.execute(
                        'SELECT * FROM contactos WHERE nombre LIKE ? OR telefono LIKE ? OR email LIKE ?',
                        (f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%')
                    )
                
                contactos = cursor.fetchall()
                conn.close()
            except Exception as e:
                flash('Error en la búsqueda. Intenta nuevamente.', 'error')
                print(f"Error en búsqueda: {e}")
    
    return render_template('buscar.html', contactos=contactos)

# Para desarrollo local
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))