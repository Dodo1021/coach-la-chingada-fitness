let currentConversationId = null;

// Cargar la conversación única del usuario
async function loadConversation() {
    try {
        const response = await fetch('/api/conversation');
        const data = await response.json();
        if (data.status === 'success') {
            currentConversationId = data.conversation_id;
            const chatMessages = document.getElementById('chat-messages');
            chatMessages.innerHTML = '';
            if (data.messages && data.messages.length > 0) {
                data.messages.forEach(message => {
                    mostrarMensaje(message[0], message[1]);
                });
            } else {
                mostrarMensaje('assistant', '¡Hola! Soy tu coach virtual de La Chingada Fitness. ¿En qué puedo ayudarte hoy?');
            }
        } else {
            throw new Error(data.message || 'Error al cargar la conversación');
        }
    } catch (error) {
        console.error('Error al cargar la conversación:', error);
        mostrarMensaje('assistant', 'Lo siento, ha ocurrido un error al cargar la conversación. Por favor, intenta de nuevo.');
    }
}

function mostrarMensaje(tipo, mensaje) {
    const chatMessages = document.getElementById('chat-messages');
    const div = document.createElement('div');
    div.className = 'message ' + (tipo === 'user' ? 'user-message' : 'assistant-message');
    div.textContent = mensaje;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Manejar el envío de mensajes

document.addEventListener('DOMContentLoaded', () => {
    const chatForm = document.getElementById('chat-form');
    const userInput = document.getElementById('user-input');

    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const mensaje = userInput.value.trim();
        if (!mensaje) return;
        mostrarMensaje('user', mensaje);
        userInput.value = '';
        userInput.disabled = true;
        try {
            const response = await fetch('/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    mensaje
                })
            });
            const data = await response.json();
            if (data.status === 'success') {
                mostrarMensaje('assistant', data.respuesta);
            } else {
                throw new Error(data.message || 'Error en la respuesta del servidor');
            }
        } catch (error) {
            console.error('Error:', error);
            mostrarMensaje('assistant', 'Lo siento, ha ocurrido un error. Por favor, intenta de nuevo.');
        } finally {
            userInput.disabled = false;
            userInput.focus();
        }
    });
    loadConversation();
}); 