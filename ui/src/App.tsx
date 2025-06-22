import { useState, useEffect, FormEvent } from 'react';
import './App.css'; // Existing App.css, can be used or replaced by Tailwind utility classes

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/message';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'bot';
}

function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Optional: Welcome message or load initial history
  useEffect(() => {
    // setMessages([{ id: 'initial-bot', text: 'Hello! How can I help you today?', sender: 'bot' }]);
  }, []);

  const handleSendMessage = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!inputValue.trim()) return;

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      text: inputValue,
      sender: 'user',
    };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ text: userMessage.text }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: 'Network response was not ok' }));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();

      const botMessage: Message = {
        id: `bot-${Date.now()}`,
        text: data.response, // Assuming API returns { response: "bot text" }
        sender: 'bot',
      };
      setMessages((prevMessages) => [...prevMessages, botMessage]);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred.';
      setError(errorMessage);
      // Optionally add an error message to the chat
      setMessages((prevMessages) => [...prevMessages, {
        id: `error-${Date.now()}`,
        text: `Error: ${errorMessage}`,
        sender: 'bot'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-2xl mx-auto p-4 bg-slate-50">
      <header className="mb-4">
        <h1 className="text-3xl font-bold text-center text-slate-700">Katana AI Chat</h1>
      </header>

      <div className="flex-grow overflow-y-auto mb-4 p-4 bg-white shadow rounded-lg space-y-4">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-xl shadow ${
                msg.sender === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-slate-200 text-slate-800'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.text}</p>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="px-4 py-2 rounded-xl shadow bg-slate-200 text-slate-800">
              <p><i>Bot is typing...</i></p>
            </div>
          </div>
        )}
         {error && !isLoading && ( // Show general error if not shown as a message already
           <div className="flex justify-center">
            <div className="px-4 py-2 rounded-xl shadow bg-red-100 text-red-700">
              <p><strong>Error communicating with server:</strong> {error}</p>
            </div>
          </div>
        )}
      </div>

      <form onSubmit={handleSendMessage} className="flex items-center gap-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Type your message..."
          className="flex-grow p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none shadow-sm"
          disabled={isLoading}
        />
        <button
          type="submit"
          className="bg-blue-500 hover:bg-blue-600 text-white font-semibold py-3 px-6 rounded-lg shadow-sm disabled:opacity-50"
          disabled={isLoading || !inputValue.trim()}
        >
          Send
        </button>
      </form>
    </div>
  );
}

export default App;
