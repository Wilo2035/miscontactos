from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'  # Necesario para los mensajes flash

# Función para conectar a la base de datos
def get_db_connection():
    conn = sqlite3.connect('contactos.db')
    conn.row_factory = sqlite3.Row
    return conn

# Función para inicializar la base de datos
def init_db():
    conn = get_db_connection()
    conn.execute('''
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

# Página principal - mostrar todos los contactos
@app.route('/')
def index():
    conn = get_db_connection()
    contactos = conn.execute('SELECT * FROM contactos ORDER BY nombre').fetchall()
    conn.close()
    return render_template('index.html', contactos=contactos)

# Página para agregar contacto
@app.route('/agregar', methods=['GET', 'POST'])
def agregar_contacto():
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        
        if nombre and telefono and email:
            conn = get_db_connection()
            conn.execute('INSERT INTO contactos (nombre, telefono, email) VALUES (?, ?, ?)',
                        (nombre, telefono, email))
            conn.commit()
            conn.close()
            flash('Contacto agregado exitosamente!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Por favor completa todos los campos', 'error')
    
    return render_template('agregar.html')

# Página para editar contacto
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar_contacto(id):
    conn = get_db_connection()
    contacto = conn.execute('SELECT * FROM contactos WHERE id = ?', (id,)).fetchone()
    
    if request.method == 'POST':
        nombre = request.form['nombre']
        telefono = request.form['telefono']
        email = request.form['email']
        
        if nombre and telefono and email:
            conn.execute('UPDATE contactos SET nombre = ?, telefono = ?, email = ? WHERE id = ?',
                        (nombre, telefono, email, id))
            conn.commit()
            conn.close()
            flash('Contacto actualizado exitosamente!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Por favor completa todos los campos', 'error')
    
    conn.close()
    return render_template('editar.html', contacto=contacto)

# Eliminar contacto
@app.route('/eliminar/<int:id>')
def eliminar_contacto(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM contactos WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    flash('Contacto eliminado exitosamente!', 'success')
    return redirect(url_for('index'))

# Buscar contactos
@app.route('/buscar', methods=['GET', 'POST'])
def buscar_contacto():
    contactos = []
    if request.method == 'POST':
        busqueda = request.form['busqueda']
        conn = get_db_connection()
        contactos = conn.execute(
            'SELECT * FROM contactos WHERE nombre LIKE ? OR telefono LIKE ? OR email LIKE ?',
            (f'%{busqueda}%', f'%{busqueda}%', f'%{busqueda}%')
        ).fetchall()
        conn.close()
    
    return render_template('buscar.html', contactos=contactos)

if __name__ == '__main__':
    init_db()  # Crear la base de datos al iniciar
    app.run(debug=True)