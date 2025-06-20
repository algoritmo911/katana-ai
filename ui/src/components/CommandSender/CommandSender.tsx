import React, { useState } from 'react';

// Dummy function for now, will be replaced with actual API call
const sendCommandToApi = async (command: object) => {
  console.log("Sending command to API:", command);
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 500));
  // Simulate success
  return { success: true, message: "Command received (simulated)" };
  // Simulate error:
  // return { success: false, message: "Error sending command (simulated)" };
};

const CommandSender: React.FC = () => {
  const [jsonInput, setJsonInput] = useState<string>('');
  const [isValidJson, setIsValidJson] = useState<boolean>(true);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);

  const exampleCommand = {
    type: "log_event",
    module: "example_module",
    args: {
      message: "Hello from UI",
      level: "INFO"
    },
    id: `cmd-${Date.now()}`
  };

  const handleInputChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = event.target.value;
    setJsonInput(text);
    setFeedbackMessage(null); // Clear feedback on new input
    try {
      JSON.parse(text);
      setIsValidJson(true);
    } catch (error) {
      setIsValidJson(false);
    }
  };

  const handleSend = async () => {
    if (!jsonInput.trim()) {
      setFeedbackMessage("Error: Command input cannot be empty.");
      setIsValidJson(false);
      return;
    }
    let commandObject;
    try {
      commandObject = JSON.parse(jsonInput);
      setIsValidJson(true);
    } catch (error) {
      setFeedbackMessage("Error: Invalid JSON format.");
      setIsValidJson(false);
      return;
    }

    setFeedbackMessage("Sending command...");
    const response = await sendCommandToApi(commandObject);
    if (response.success) {
      setFeedbackMessage(`Success: ${response.message}`);
    } else {
      setFeedbackMessage(`Error: ${response.message}`);
    }
  };

  const handleClear = () => {
    setJsonInput('');
    setIsValidJson(true);
    setFeedbackMessage(null);
  };

  const handleLoadExample = () => {
    setJsonInput(JSON.stringify(exampleCommand, null, 2));
    setIsValidJson(true);
    setFeedbackMessage("Example command loaded.");
  };

  return (
    <div className="bg-slate-700 p-6 rounded-lg shadow-xl">
      <h2 className="text-2xl font-semibold mb-4 text-white">Command Sender</h2>

      <textarea
        value={jsonInput}
        onChange={handleInputChange}
        placeholder='Enter JSON command here...
Example:
{
  "type": "ping",
  "module": "system",
  "id": "ui-ping-123"
}'
        rows={10}
        className={`w-full p-3 rounded-md text-sm font-mono
                    bg-slate-800 text-slate-200 border
                    ${isValidJson ? 'border-slate-600' : 'border-red-500 focus:border-red-500'}
                    focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-colors`}
      />
      {!isValidJson && jsonInput.length > 0 && (
        <p className="text-red-400 text-xs mt-1">Invalid JSON format.</p>
      )}

      {feedbackMessage && (
        <div className={`mt-3 p-2 rounded-md text-xs text-center
                       ${feedbackMessage.startsWith('Error:') ? 'bg-red-500/20 text-red-300' :
                         feedbackMessage.startsWith('Success:') ? 'bg-green-500/20 text-green-300' : 'bg-blue-500/20 text-blue-300'}`}>
          {feedbackMessage}
        </div>
      )}

      <div className="mt-4 flex flex-wrap gap-3">
        <button
          onClick={handleSend}
          disabled={!isValidJson && jsonInput.length > 0}
          className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-md transition-colors
                     disabled:bg-slate-500 disabled:cursor-not-allowed"
        >
          Send Command
        </button>
        <button
          onClick={handleClear}
          className="flex-1 bg-slate-500 hover:bg-slate-600 text-white font-semibold py-2 px-4 rounded-md transition-colors"
        >
          Clear
        </button>
        <button
          onClick={handleLoadExample}
          className="flex-1 bg-teal-600 hover:bg-teal-700 text-white font-semibold py-2 px-4 rounded-md transition-colors"
        >
          Load Example
        </button>
      </div>
    </div>
  );
};

export default CommandSender;
