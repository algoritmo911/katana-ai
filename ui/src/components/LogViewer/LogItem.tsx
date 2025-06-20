import React from 'react';

export interface LogEntry {
  timestamp: number | string; // Can be number (epoch) or ISO string
  level: "INFO" | "WARN" | "ERROR" | "DEBUG" | string; // Allow other strings for flexibility
  module: string;
  message: string;
  [key: string]: any; // Allow other properties
}

interface LogItemProps {
  log: LogEntry;
}

const LogItem: React.FC<LogItemProps> = ({ log }) => {
  const getLevelClass = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'text-red-400 border-red-500/50';
      case 'WARN':
        return 'text-yellow-400 border-yellow-500/50';
      case 'INFO':
        return 'text-blue-400 border-blue-500/50';
      case 'DEBUG':
        return 'text-gray-400 border-gray-500/50';
      default:
        return 'text-slate-300 border-slate-500/50';
    }
  };

  const getLevelBgClass = (level: string) => {
    switch (level.toUpperCase()) {
      case 'ERROR':
        return 'bg-red-500/20';
      case 'WARN':
        return 'bg-yellow-500/20';
      case 'INFO':
        return 'bg-blue-500/20';
      case 'DEBUG':
        return 'bg-gray-500/20';
      default:
        return 'bg-slate-600/20';
    }
  }

  const formattedTimestamp = typeof log.timestamp === 'number'
    ? new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
    : new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });


  return (
    <div className={`p-2.5 border-b border-slate-700/50 font-mono text-xs hover:bg-slate-700/30 transition-colors duration-150 ${getLevelClass(log.level)}`}>
      <div className="flex items-center">
        <span className="mr-3 text-slate-500 min-w-[60px]">{formattedTimestamp}</span>
        <span
          className={`font-semibold mr-2 px-1.5 py-0.5 rounded text-tiny ${getLevelBgClass(log.level)}`}
        >
          {log.level.toUpperCase()}
        </span>
        <span className="mr-3 text-purple-400 font-medium">[{log.module}]</span>
        <span className="whitespace-pre-wrap break-all">{log.message}</span>
      </div>
      {/* Optionally display other log properties if they exist */}
      {Object.entries(log).filter(([key]) => !['timestamp', 'level', 'module', 'message'].includes(key)).length > 0 && (
        <div className="mt-1 pl-12 text-slate-500 text-tiny">
          {Object.entries(log).map(([key, value]) => {
            if (!['timestamp', 'level', 'module', 'message'].includes(key)) {
              return <span key={key} className="mr-2">{key}: {JSON.stringify(value)}</span>;
            }
            return null;
          })}
        </div>
      )}
    </div>
  );
};

export default LogItem;
