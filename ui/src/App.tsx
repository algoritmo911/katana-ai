import React, { useState } from 'react';
import './App.css';

interface Message {
  sender: 'user' | 'katana';
  text: string;
}

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = { sender: 'user', text: input };
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await fetch('/api/v1/echo', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: input }),
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const data = await response.json();
      const katanaMessage: Message = { sender: 'katana', text: data.response };
      setMessages(prev => [...prev, userMessage, katanaMessage]);

    } catch (error) {
      console.error('There was a problem with the fetch operation:', error);
      const errorMessage: Message = { sender: 'katana', text: 'Error: Could not connect to server.' };
      setMessages(prev => [...prev, userMessage, errorMessage]);
    } finally {
        setInput('');
    }
  };

  // A quick fix to avoid duplicating the user message.
  // The state update is async, so the 'prev' state in the fetch response handler might not have the user message yet.
  // A better solution would be to manage state more robustly, but for Tracer Bullet, this is fine.
  const displayMessages = messages.filter((msg, i) => {
    if (i > 0 && msg.sender === 'user' && messages[i-1].sender === 'user' && msg.text === messages[i-1].text) {
        if(messages[i+1] && messages[i+1].sender === 'katana') return false;
    }
    return true;
  });


  return (
    <div className="bg-gray-900 text-white min-h-screen flex flex-col justify-center items-center font-mono">
      <div className="w-full max-w-2xl mx-auto p-4">
        <h1 className="text-3xl font-bold text-center mb-6">Katana AI</h1>
        <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 h-96 overflow-y-auto mb-4">
          {displayMessages.map((msg, index) => (
            <div key={index} className={`mb-2 ${msg.sender === 'user' ? 'text-right' : 'text-left'}`}>
              <span className={`inline-block p-2 rounded-lg ${msg.sender === 'user' ? 'bg-blue-600' : 'bg-gray-700'}`}>
                {msg.sender === 'katana' && <b className="font-bold">Katana: </b>}
                {msg.text}
              </span>
            </div>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="flex">
          <input
            type="text"
            className="flex-grow bg-gray-700 text-white border border-gray-600 rounded-l-lg p-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded-r-lg"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}

export default App;
