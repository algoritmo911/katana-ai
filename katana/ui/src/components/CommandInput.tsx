import React, { useState } from 'react'; // React import was missing in user prompt

type Props = {
  onSend: (text: string) => void;
};

const CommandInput: React.FC<Props> = ({ onSend }) => {
  const [input, setInput] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSend(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (input.trim()) { // Ensure there's input before sending
        onSend(input.trim());
        setInput('');
      }
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center p-2 bg-gray-100 dark:bg-gray-800 border-t border-gray-300 dark:border-gray-700">
      <input
        type="text"
        value={input}
        onChange={e => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Введите команду, нажмите Enter"
        className="flex-grow p-2 border border-gray-300 dark:border-gray-600 rounded-l-md shadow-sm focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
        autoFocus
      />
      <button
        type="submit"
        disabled={!input.trim()}
        className="px-6 py-2 bg-blue-600 text-white font-semibold rounded-r-md shadow-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-opacity-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Отправить
      </button>
    </form>
  );
};

export default CommandInput;
