import React, { useState, useEffect } from 'react';
import LogItem from './LogItem';

// Dummy function for now, will be replaced with actual API call
const fetchLogsFromApi = async (filters: any) => {
  console.log("Fetching logs from API with filters:", filters);
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 1000));
  // Simulate success
  return {
    success: true,
    data: [
      { timestamp: Date.now() - 5000, level: "INFO", module: "system", message: "System initialized." },
      { timestamp: Date.now() - 4000, level: "WARN", module: "network", message: "High latency detected." },
      { timestamp: Date.now() - 3000, level: "ERROR", module: "database", message: "Failed to connect to DB." },
      { timestamp: Date.now() - 2000, level: "INFO", module: "telegram_bot", message: "Command '/start' received." },
      { timestamp: Date.now() - 1000, level: "DEBUG", module: "ui_interaction", message: "Button clicked: SendCommand" },
    ]
  };
  // Simulate error:
  return { success: false, message: "Error fetching logs (simulated)" };
};

const LogViewer: React.FC = () => {
  const [logs, setLogs] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [filterLevel, setFilterLevel] = useState<string>('');
  const [filterModule, setFilterModule] = useState<string>('');
  const [filterDate, setFilterDate] = useState<string>(''); // Could be more complex date picker

  const loadLogs = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    const filters = { level: filterLevel, module: filterModule, date: filterDate };
    const response: { success: boolean; data?: any[]; message?: string } = await fetchLogsFromApi(filters);
    if (response.success) {
      setLogs(response.data || []);
    } else {
      setErrorMessage(response.message || "Failed to fetch logs.");
      setLogs([]);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    loadLogs();
    // Optional: set up polling or WebSocket for real-time logs
  }, []); // Initial load

  const handleFilterSubmit = (event?: React.FormEvent) => {
    if (event) event.preventDefault();
    loadLogs();
  };

  const displayedLogs = logs.filter(log => {
    if (filterLevel && log.level !== filterLevel) return false;
    if (filterModule && !log.module.toLowerCase().includes(filterModule.toLowerCase())) return false;
    // Date filtering would be more complex here based on `filterDate` format
    return true;
  });


  return (
    <div className="bg-slate-700 p-6 rounded-lg shadow-xl text-white col-span-1 md:col-span-2">
      <h2 className="text-2xl font-semibold mb-4">Log Viewer</h2>

      <form onSubmit={handleFilterSubmit} className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-4 p-4 bg-slate-800/50 rounded-lg">
        <div>
          <label htmlFor="filterLevel" className="block text-sm font-medium text-slate-300 mb-1">Log Level</label>
          <select
            id="filterLevel"
            value={filterLevel}
            onChange={(e) => setFilterLevel(e.target.value)}
            className="w-full p-2 rounded-md text-sm bg-slate-600 text-white border border-slate-500 focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="">All Levels</option>
            <option value="INFO">INFO</option>
            <option value="WARN">WARN</option>
            <option value="ERROR">ERROR</option>
            <option value="DEBUG">DEBUG</option>
          </select>
        </div>
        <div>
          <label htmlFor="filterModule" className="block text-sm font-medium text-slate-300 mb-1">Module</label>
          <input
            type="text"
            id="filterModule"
            placeholder="e.g., system, network"
            value={filterModule}
            onChange={(e) => setFilterModule(e.target.value)}
            className="w-full p-2 rounded-md text-sm bg-slate-600 text-white border border-slate-500 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div>
          <label htmlFor="filterDate" className="block text-sm font-medium text-slate-300 mb-1">Date</label>
          <input
            type="date" // Simple date picker, can be enhanced
            id="filterDate"
            value={filterDate}
            onChange={(e) => setFilterDate(e.target.value)}
            className="w-full p-2 rounded-md text-sm bg-slate-600 text-white border border-slate-500 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>
        <div className="flex items-end">
          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-md transition-colors text-sm"
          >
            Apply Filters
          </button>
        </div>
      </form>

      {isLoading && (
        <div className="flex justify-center items-center h-40">
          <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-blue-400"></div>
          <p className="ml-3 text-slate-300">Loading logs...</p>
        </div>
      )}
      {!isLoading && errorMessage && (
        <div className="bg-red-500/20 text-red-300 p-3 rounded-md text-center">
          <p>{errorMessage}</p>
          <button
            onClick={loadLogs}
            className="mt-2 bg-red-700 hover:bg-red-800 text-white font-semibold py-1 px-3 rounded-md text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      )}
      {!isLoading && !errorMessage && (
        <div className="bg-slate-800/50 rounded-lg shadow-inner max-h-96 overflow-y-auto">
          {displayedLogs.length > 0 ? (
            displayedLogs.map((log, index) => (
              <LogItem key={index} log={log} />
            ))
          ) : (
            <p className="p-4 text-center text-slate-400">No logs found or matching filters.</p>
          )}
        </div>
      )}
    </div>
  );
};

export default LogViewer;
