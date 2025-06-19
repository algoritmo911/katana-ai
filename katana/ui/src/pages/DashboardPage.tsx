import React, { useState, useEffect, useRef } from 'react';
import CommandInput from '../components/CommandInput';
import { loadMemory, saveMemory, MemoryEntry } from '../memory';
import { triggerSearch } from '../triggerSearch';

type Message = {
  id: number;
  role: 'user' | 'katana';
  text: string;
  timestamp?: string;
};

const DashboardPage: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [nextIdState, setNextIdState] = useState(() => {
    const saved = loadMemory();
    if (saved.length > 0 && saved[saved.length - 1]?.id != null) {
      const numericIds = saved.map(m => Number(m.id)).filter(id => !isNaN(id));
      if (numericIds.length > 0) {
        return Math.max(...numericIds) + 1;
      }
    }
    return Date.now();
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  useEffect(() => {
    const initialMemoryEntries = loadMemory();
    if (initialMemoryEntries.length) {
      const initialMessages: Message[] = initialMemoryEntries.map(m => ({
          id: Number(m.id),
          role: m.role,
          text: m.text,
          timestamp: m.timestamp || new Date().toISOString()
      }));
      setMessages(initialMessages);
      const lastId = initialMessages[initialMessages.length - 1]?.id;
      if (lastId != null) {
        setNextIdState( Number(lastId) + 1 );
      } else {
        setNextIdState(Date.now() + initialMessages.length + 1);
      }
    } else {
      const welcomeMsgId = Date.now();
      setMessages([
        {
          id: welcomeMsgId,
          role: "katana",
          text: "Katana Dashboard ⚔️ Chat Ready. Send a command.",
          timestamp: new Date().toISOString()
        },
      ]);
      setNextIdState(welcomeMsgId + 1);
    }
  }, []);

  useEffect(() => {
    if (messages.length > 0) {
      const messagesToSave: MemoryEntry[] = messages.map(m => ({
          id: m.id,
          role: m.role,
          text: m.text,
          timestamp: m.timestamp
      }));
      saveMemory(messagesToSave);
    }
  }, [messages]);

  const onSend = (text: string) => {
    if (!text.trim()) return;

    const currentId = nextIdState;
    const userMsg: Message = {
        id: currentId,
        role: 'user',
        text,
        timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMsg]);

    setTimeout(() => {
      const replyText = triggerSearch(text) || "Katana is processing... (default reply)";
      const katanaMsg: Message = {
        id: currentId + 1,
        role: 'katana',
        text: replyText,
        timestamp: new Date().toISOString()
      };
      setMessages(prev => [...prev, katanaMsg]);
      setNextIdState(currentId + 2);
    }, 300);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-3xl mx-auto">
      <header className="p-3 border-b dark:border-gray-700 sticky top-0 bg-gray-100 dark:bg-gray-900 z-10">
        <h2 className="text-xl font-semibold text-center text-gray-800 dark:text-gray-100">
          Katana Command Interface
        </h2>
      </header>

      <div
        className="flex-grow overflow-y-auto p-4 space-y-4 bg-white dark:bg-gray-800 shadow-inner rounded-b-md"
      >
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs sm:max-w-sm md:max-w-md lg:max-w-lg px-3 py-2 rounded-xl shadow-md whitespace-pre-wrap break-words ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-800 dark:bg-gray-700 dark:text-gray-100'
              }`}
            >
              <p className="font-bold text-xs capitalize">{msg.role === 'user' ? 'You' : 'Katana'}</p>
              <p className="text-sm">{msg.text}</p>
              {msg.timestamp && (
                <p className={`text-xs mt-1 ${
                  msg.role === 'user' ? 'text-blue-200 text-right' : 'text-gray-400 dark:text-gray-500 text-left'
                }`}>
                  {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </p>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="mt-auto sticky bottom-0 bg-gray-100 dark:bg-gray-900 py-2 border-t dark:border-gray-700">
        <CommandInput onSend={onSend} />
      </div>
    </div>
  );
};

export default DashboardPage;
