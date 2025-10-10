// frontend/js/chatbot.js

document.addEventListener('DOMContentLoaded', () => {
    const chatBubble = document.getElementById('chat-bubble');
    const chatWindow = document.getElementById('chat-window');
    const closeChatBtn = document.getElementById('close-chat');
    const sendChatBtn = document.getElementById('send-chat');
    const chatInput = document.getElementById('chat-input');
    const chatBody = document.getElementById('chat-body');

    // Toggle chat window visibility
    chatBubble.addEventListener('click', () => {
        chatWindow.classList.toggle('hidden-chat');
    });

    closeChatBtn.addEventListener('click', () => {
        chatWindow.classList.add('hidden-chat');
    });

    // Handle sending a message
    const sendMessage = async () => {
        const messageText = chatInput.value.trim();
        if (messageText === '') return;

        // Display user's message
        addMessageToChat(messageText, 'user');
        chatInput.value = '';

        try {
            // Send message to backend
            const response = await fetch('http://127.0.0.1:8000/api/chatbot', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: messageText }),
            });

            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            
            // Display bot's reply
            addMessageToChat(data.reply, 'bot');

        } catch (error) {
            console.error('Error fetching chatbot response:', error);
            addMessageToChat('Sorry, I seem to be having trouble connecting. Please try again later.', 'bot');
        }
    };

    // Helper function to add a message to the chat window
    const addMessageToChat = (text, sender) => {
        const messageElement = document.createElement('div');
        messageElement.classList.add('chat-message', sender);
        messageElement.textContent = text;
        chatBody.appendChild(messageElement);
        // Scroll to the latest message
        chatBody.scrollTop = chatBody.scrollHeight;
    };

    sendChatBtn.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
            sendMessage();
        }
    });
});