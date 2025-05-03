import os
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
SECRET_KEY = os.environ.get("SECRET_KEY")
ASSISTANT_ID = os.environ.get("ASSISTANT_ID")

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from openai import OpenAI
from database import init_db, get_user, create_user, create_conversation, save_message, get_user_conversations, get_conversation_messages, delete_conversation, update_password, delete_user, get_or_create_user_conversation

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = 3600  # 1 hora

# Configuración de OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Inicializar la base de datos
init_db()

@app.before_request
def require_login():
    allowed_routes = ['login', 'register', 'static']
    if request.endpoint not in allowed_routes and 'user_id' not in session:
        return redirect(url_for('login'))

@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('chat'))
    return render_template('index.html')

@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    conversations = get_user_conversations(user_id)
    return render_template('chat.html', conversations=conversations)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        remember = request.form.get('remember') == 'on'
        
        user = get_user(username)
        if user and user[2] == password:  # user[2] es la contraseña
            session['user_id'] = user[0]  # user[0] es el id
            session['username'] = user[1]  # user[1] es el nombre de usuario
            if remember:
                session.permanent = True
            return redirect(url_for('chat'))
        else:
            return render_template('login.html', error='Usuario o contraseña incorrectos')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return render_template('register.html', error='Las contraseñas no coinciden')

        try:
            user_id = create_user(username, password)
            session['user_id'] = user_id
            return redirect(url_for('chat'))
        except Exception as e:
            return render_template('register.html', error='El usuario ya existe')

    return render_template('register.html')

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Usuario no autenticado"}), 401
    
    data = request.json
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    user = get_user(session['username'])
    if user and user[2] == current_password:
        if update_password(session['user_id'], new_password):
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Error al actualizar la contraseña"}), 500
    else:
        return jsonify({"status": "error", "message": "Contraseña actual incorrecta"}), 400

@app.route('/delete_account', methods=['POST'])
def delete_account():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Usuario no autenticado"}), 401
    
    data = request.json
    password = data.get('password')
    
    user = get_user(session['username'])
    if user and user[2] == password:
        if delete_user(session['user_id']):
            session.clear()
            return jsonify({"status": "success"})
        else:
            return jsonify({"status": "error", "message": "Error al eliminar la cuenta"}), 500
    else:
        return jsonify({"status": "error", "message": "Contraseña incorrecta"}), 400

@app.route('/api/chat', methods=['POST'])
def handle_chat():
    try:
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Usuario no autenticado"}), 401
            
        data = request.json
        mensaje = data.get('mensaje')
        conversation_id = data.get('conversation_id')
        
        # Si es una nueva conversación
        if not conversation_id:
            thread = client.beta.threads.create()
            conversation_id = create_conversation(session['user_id'], thread.id)
            thread_id = thread.id
        else:
            # Obtener el thread_id de la conversación existente
            result = get_conversation_messages(conversation_id)
            if not result:
                return jsonify({"status": "error", "message": "Conversación no encontrada"}), 404
            thread_id = result[0]
        
        # Agregar mensaje del usuario
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=mensaje
        )
        
        # Guardar mensaje del usuario en la base de datos
        save_message(conversation_id, "user", mensaje)
        
        # Ejecutar el asistente
        run = client.beta.threads.runs.create_and_poll(
            thread_id=thread_id,
            assistant_id=ASSISTANT_ID
        )
        
        # Obtener la respuesta
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        respuesta = messages.data[0].content[0].text.value
        
        # Guardar respuesta del asistente en la base de datos
        save_message(conversation_id, "assistant", respuesta)
        
        return jsonify({
            "status": "success",
            "respuesta": respuesta,
            "conversation_id": conversation_id
        })
        
    except Exception as e:
        print(f"Error en handle_chat: {str(e)}")  # Para debugging
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route('/api/conversations')
def get_conversations():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Usuario no autenticado"}), 401
        
    conversations = get_user_conversations(session['user_id'])
    return jsonify({
        "status": "success",
        "conversations": conversations
    })

@app.route('/api/conversation')
def get_conversation():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Usuario no autenticado"}), 401
    user_id = session['user_id']
    conversation_id, _ = get_or_create_user_conversation(user_id)
    result = get_conversation_messages(conversation_id)
    if not result:
        return jsonify({"status": "error", "message": "Conversación no encontrada"}), 404
    thread_id, messages = result
    return jsonify({
        "status": "success",
        "messages": messages,
        "conversation_id": conversation_id
    })

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('home'))

@app.route('/delete_conversation/<int:conversation_id>', methods=['POST'])
def delete_conversation_route(conversation_id):
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Usuario no autenticado"}), 401
    
    if delete_conversation(conversation_id):
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Error al eliminar la conversación"}), 500

if __name__ == '__main__':
    app.run(debug=True) 