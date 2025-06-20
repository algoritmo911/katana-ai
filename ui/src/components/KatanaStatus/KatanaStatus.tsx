import React, { useState, useEffect } from 'react';

// Dummy function for now, will be replaced with actual API call
const fetchStatusFromApi = async () => {
  console.log("Fetching status from API...");
  // Simulate API call
  await new Promise(resolve => setTimeout(resolve, 750));
  // Simulate success
  return {
    success: true,
    data: {
      status: "Online (Simulated)",
      uptime: "0h 5m 12s (Simulated)",
      ping: "120ms (Simulated)",
      lastChecked: new Date().toLocaleTimeString()
    }
  };
  // Simulate error:
  // return { success: false, message: "Error fetching status (simulated)" };
};

const KatanaStatus: React.FC = () => {
  const [statusData, setStatusData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const loadStatus = async () => {
    setIsLoading(true);
    setErrorMessage(null);
    const response = await fetchStatusFromApi();
    if (response.success) {
      setStatusData(response.data);
    } else {
      setErrorMessage(response.message || "Failed to fetch status.");
      setStatusData(null);
    }
    setIsLoading(false);
  };

  useEffect(() => {
    loadStatus();
    // Optional: set up a poller if desired for auto-refresh, e.g. every 30 seconds
    // const intervalId = setInterval(loadStatus, 30000);
    // return () => clearInterval(intervalId);
  }, []);

  return (
    <div className="bg-slate-700 p-6 rounded-lg shadow-xl text-white">
      <h2 className="text-2xl font-semibold mb-4">Katana Status</h2>
      {isLoading && (
        <div className="flex justify-center items-center h-24">
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-400"></div>
          <p className="ml-3 text-slate-300">Loading status...</p>
        </div>
      )}
      {!isLoading && errorMessage && (
        <div className="bg-red-500/20 text-red-300 p-3 rounded-md text-center">
          <p>{errorMessage}</p>
          <button
            onClick={loadStatus}
            className="mt-2 bg-red-700 hover:bg-red-800 text-white font-semibold py-1 px-3 rounded-md text-sm transition-colors"
          >
            Retry
          </button>
        </div>
      )}
      {!isLoading && !errorMessage && statusData && (
        <div className="space-y-3">
          <div className="flex justify-between items-center">
            <span className="text-slate-400 font-medium">Overall Status:</span>
            <span className={`font-bold px-2 py-1 rounded-full text-sm ${
              statusData.status?.toLowerCase().includes('online')
                ? 'bg-green-500/30 text-green-300'
                : 'bg-red-500/30 text-red-300'
            }`}>
              {statusData.status || 'N/A'}
            </span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400 font-medium">Uptime:</span>
            <span className="text-slate-200">{statusData.uptime || 'N/A'}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-400 font-medium">Ping:</span>
            <span className="text-slate-200">{statusData.ping || 'N/A'}</span>
          </div>
          <div className="border-t border-slate-600 my-3"></div>
          <div className="flex justify-between items-center">
            <button
              onClick={loadStatus}
              className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded-md transition-colors text-sm"
            >
              Refresh Status
            </button>
          </div>
           <p className="text-xs text-slate-500 text-center mt-2">Last checked: {statusData.lastChecked}</p>
        </div>
      )}
    </div>
  );
};

export default KatanaStatus;
