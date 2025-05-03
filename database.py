import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    
    # Eliminar tablas existentes si existen
    c.execute('DROP TABLE IF EXISTS messages')
    c.execute('DROP TABLE IF EXISTS conversations')
    c.execute('DROP TABLE IF EXISTS users')
    
    # Crear tabla de usuarios
    c.execute('''CREATE TABLE users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Crear tabla de conversaciones
    c.execute('''CREATE TABLE conversations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  thread_id TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Crear tabla de mensajes
    c.execute('''CREATE TABLE messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  conversation_id INTEGER NOT NULL,
                  role TEXT NOT NULL,
                  content TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (conversation_id) REFERENCES conversations (id))''')
    
    conn.commit()
    conn.close()

def create_user(username, password):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    try:
        c.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                  (username, password))
        user_id = c.lastrowid
        conn.commit()
        return user_id
    except sqlite3.IntegrityError:
        raise Exception("El usuario ya existe")
    finally:
        conn.close()

def get_user(username):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    try:
        c.execute('SELECT id, username, password FROM users WHERE username = ?', (username,))
        user = c.fetchone()
        return user
    finally:
        conn.close()

def create_conversation(user_id, thread_id):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute('INSERT INTO conversations (user_id, thread_id) VALUES (?, ?)',
              (user_id, thread_id))
    conversation_id = c.lastrowid
    conn.commit()
    conn.close()
    return conversation_id

def get_user_conversations(user_id):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute('''SELECT c.id, c.thread_id, c.created_at, 
                 (SELECT content FROM messages WHERE conversation_id = c.id ORDER BY created_at DESC LIMIT 1) as last_message
                 FROM conversations c
                 WHERE c.user_id = ?
                 ORDER BY c.created_at DESC''', (user_id,))
    conversations = c.fetchall()
    conn.close()
    return conversations

def get_conversation_messages(conversation_id):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    
    # Verificar que la conversación pertenece al usuario
    c.execute('SELECT thread_id FROM conversations WHERE id = ?', (conversation_id,))
    result = c.fetchone()
    if not result:
        conn.close()
        return None
    
    thread_id = result[0]
    
    # Obtener los mensajes
    c.execute('''SELECT role, content, created_at
                 FROM messages
                 WHERE conversation_id = ?
                 ORDER BY created_at ASC''', (conversation_id,))
    
    messages = c.fetchall()
    conn.close()
    return thread_id, messages

def save_message(conversation_id, role, content):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute('INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)',
              (conversation_id, role, content))
    conn.commit()
    conn.close()

def delete_conversation(conversation_id):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    try:
        # Primero eliminar los mensajes asociados
        c.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation_id,))
        # Luego eliminar la conversación
        c.execute('DELETE FROM conversations WHERE id = ?', (conversation_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al eliminar conversación: {str(e)}")
        return False
    finally:
        conn.close()

def update_password(user_id, new_password):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    try:
        c.execute('UPDATE users SET password = ? WHERE id = ?', (new_password, user_id))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al actualizar contraseña: {str(e)}")
        return False
    finally:
        conn.close()

def delete_user(user_id):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    try:
        # Primero eliminar todas las conversaciones del usuario
        c.execute('SELECT id FROM conversations WHERE user_id = ?', (user_id,))
        conversations = c.fetchall()
        for conversation in conversations:
            # Eliminar mensajes de la conversación
            c.execute('DELETE FROM messages WHERE conversation_id = ?', (conversation[0],))
            # Eliminar la conversación
            c.execute('DELETE FROM conversations WHERE id = ?', (conversation[0],))
        
        # Finalmente eliminar el usuario
        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error al eliminar usuario: {str(e)}")
        return False
    finally:
        conn.close()

def get_or_create_user_conversation(user_id):
    conn = sqlite3.connect('conversations.db')
    c = conn.cursor()
    c.execute('SELECT id, thread_id FROM conversations WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    if result:
        conversation_id, thread_id = result
    else:
        thread_id = f"thread_{user_id}_{int(datetime.now().timestamp())}"
        c.execute('INSERT INTO conversations (user_id, thread_id) VALUES (?, ?)', (user_id, thread_id))
        conversation_id = c.lastrowid
        conn.commit()
    conn.close()
    return conversation_id, thread_id 