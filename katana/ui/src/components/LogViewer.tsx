import React, { useState, useEffect, useCallback, ChangeEvent } from 'react';

interface LogEntry {
  timestamp: string;
  level: string;
  module: string;
  message: string;
  // Optional: add an 'id' if logs have unique IDs, for React keys
  // id: string;
}

const LOGS_PER_PAGE = 50;

const LogViewer: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState<number>(1);
  const [hasMore, setHasMore] = useState<boolean>(true);
  const [initialLoadDone, setInitialLoadDone] = useState<boolean>(false);

  const [selectedLevel, setSelectedLevel] = useState<string>(""); // "" means ALL
  const [currentSearchTerm, setCurrentSearchTerm] = useState<string>(""); // For the input field
  const [appliedSearchTerm, setAppliedSearchTerm] = useState<string>(""); // For the actual search query

  const fetchLogs = useCallback(async (currentPage: number, level: string, search: string) => {
    // Prevent multiple concurrent loads for pagination if already loading more for the *same* filter set
    if (loading && currentPage > 1 && level === selectedLevel && search === appliedSearchTerm) return;

    setLoading(true);
    setError(null);

    let url = `/api/logs?page=${currentPage}&limit=${LOGS_PER_PAGE}`;
    if (level && level !== "ALL") {
      url += `&level=${level}`;
    }
    if (search) {
      url += `&search=${encodeURIComponent(search)}`;
    }

    try {
      const response = await fetch(url);
      if (!response.ok) {
        let errorDetail = `Error fetching logs: ${response.statusText}`;
        try {
            const errorData = await response.json();
            errorDetail = errorData.detail || errorDetail;
        } catch (jsonError) {
            // Ignore if response is not JSON
        }
        throw new Error(errorDetail);
      }
      const newLogs: LogEntry[] = await response.json();

      const newLogs: LogEntry[] = await response.json();

      setLogs(prevLogs => (currentPage === 1 ? newLogs : [...prevLogs, ...newLogs]));
      setHasMore(newLogs.length === LOGS_PER_PAGE);

      if (!initialLoadDone) {
        setInitialLoadDone(true);
      }

    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('An unknown error occurred.');
      }
      setHasMore(false);
      if (!initialLoadDone) {
        setInitialLoadDone(true);
      }
    } finally {
      setLoading(false);
    }
  }, [loading, initialLoadDone, selectedLevel, appliedSearchTerm]); // Dependencies for useCallback

  useEffect(() => {
    // This effect triggers fetching when page, selectedLevel, or appliedSearchTerm changes.
    // When selectedLevel or appliedSearchTerm change, page is reset to 1,
    // which then triggers this effect.
    fetchLogs(page, selectedLevel, appliedSearchTerm);
  }, [page, selectedLevel, appliedSearchTerm, fetchLogs]);

  const handleLevelChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const newLevel = event.target.value;
    setSelectedLevel(newLevel);
    setPage(1);
    setLogs([]); // Clear existing logs
    setHasMore(true); // Assume there might be more logs with new filter
    setInitialLoadDone(false); // Reset for loading indicator
  };

  const handleSearchInputChange = (event: ChangeEvent<HTMLInputElement>) => {
    setCurrentSearchTerm(event.target.value);
  };

  const applySearchTerm = () => {
    setAppliedSearchTerm(currentSearchTerm);
    setPage(1);
    setLogs([]);
    setHasMore(true);
    setInitialLoadDone(false);
  };

  const loadMoreLogs = () => {
    if (!loading && hasMore) {
      setPage(prevPage => prevPage + 1);
    }
  };

  const getLogLevelStyle = (level: string): React.CSSProperties => {
    switch (level.toUpperCase()) {
      case 'DEBUG':
        return { color: 'gray' };
      case 'INFO':
        return { color: 'blue' };
      case 'WARNING':
        return { color: 'orange' };
      case 'ERROR':
        return { color: 'red', fontWeight: 'bold' };
      case 'CRITICAL':
        return { color: 'darkred', fontWeight: 'bold', backgroundColor: '#ffeeee' };
      default:
        return {};
    }
  };

  const styles: { [key: string]: React.CSSProperties } = {
    container: {
      fontFamily: 'Arial, sans-serif',
      padding: '20px',
      maxWidth: '1200px',
      margin: '0 auto',
    },
    filtersContainer: {
      marginBottom: '20px',
      display: 'flex',
      gap: '20px',
      alignItems: 'center',
    },
    filterGroup: {
      display: 'flex',
      flexDirection: 'column',
    },
    label: {
      marginBottom: '5px',
      fontSize: '0.9em',
      color: '#333',
    },
    selectInput: {
      padding: '8px',
      borderRadius: '4px',
      border: '1px solid #ccc',
      minWidth: '150px',
    },
    textInput: {
      padding: '8px',
      borderRadius: '4px',
      border: '1px solid #ccc',
      marginRight: '10px',
    },
    searchButton: {
      padding: '8px 15px',
      backgroundColor: '#28a745',
      color: 'white',
      border: 'none',
      borderRadius: '4px',
      cursor: 'pointer',
    },
    logEntry: {
      borderBottom: '1px solid #eee',
      padding: '8px 0',
      marginBottom: '5px',
      whiteSpace: 'pre-wrap', // To respect newlines and spacing in messages
      wordBreak: 'break-all', // To break long words/strings
    },
    logTimestamp: {
      color: '#555',
      fontSize: '0.9em',
      marginRight: '10px',
    },
    logLevel: {
      fontWeight: 'bold',
      marginRight: '10px',
      minWidth: '70px', // For alignment
      display: 'inline-block',
    },
    logModule: {
      color: 'green',
      marginRight: '10px',
    },
    logMessage: {
      // display: 'inline', // Allow message to flow with other parts
    },
    button: {
      padding: '10px 15px',
      fontSize: '1em',
      cursor: 'pointer',
      backgroundColor: '#007bff',
      color: 'white',
      border: 'none',
      borderRadius: '4px',
      margin: '20px 0',
    },
    buttonDisabled: {
      backgroundColor: '#ccc',
      cursor: 'not-allowed',
    },
    error: {
      color: 'red',
      border: '1px solid red',
      padding: '10px',
      borderRadius: '4px',
    },
    loading: {
      textAlign: 'center',
      padding: '20px',
      fontSize: '1.2em',
    }
  };

  if (!initialLoadDone && loading) {
    return <div style={styles.loading}>Loading logs...</div>;
  }

  if (error) {
    return <div style={styles.error}>Error fetching logs: {error}</div>;
  }

  if (initialLoadDone && logs.length === 0 && !hasMore) {
     return <div style={styles.container}>No log entries found.</div>;
  }

  return (
    <div style={styles.container}>
      <h2>Katana Application Logs</h2>

      <div style={styles.filtersContainer}>
        <div style={styles.filterGroup}>
          <label htmlFor="level-filter" style={styles.label}>Log Level:</label>
          <select
            id="level-filter"
            value={selectedLevel}
            onChange={handleLevelChange}
            style={styles.selectInput}
          >
            <option value="">All Levels</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>
        </div>
        <div style={styles.filterGroup}>
          <label htmlFor="search-input" style={styles.label}>Search Logs:</label>
          <div>
            <input
              id="search-input"
              type="text"
              value={currentSearchTerm}
              onChange={handleSearchInputChange}
              placeholder="Enter search term..."
              style={styles.textInput}
            />
            <button onClick={applySearchTerm} style={styles.searchButton}>Search</button>
          </div>
        </div>
      </div>

      <div>
        {logs.map((log, index) => (
          // Using index as key is okay if list is append-only and items don't reorder.
          // If logs could be prepended or reordered, a unique ID per log entry would be better.
          <div key={index} style={styles.logEntry} className={`log-entry log-level-${log.level.toUpperCase()}`}>
            <span style={styles.logTimestamp}>{log.timestamp}</span>
            <span style={{ ...styles.logLevel, ...getLogLevelStyle(log.level) }}>
              {log.level}
            </span>
            <span style={styles.logModule}>[{log.module}]</span>
            <span style={styles.logMessage}>{log.message}</span>
          </div>
        ))}
      </div>
      {loading && <div style={styles.loading}>Loading more...</div>}
      {hasMore && !loading && (
        <button
          onClick={loadMoreLogs}
          style={styles.button}
          disabled={loading}
        >
          Load More
        </button>
      )}
      {!hasMore && initialLoadDone && <p>No more logs to load.</p>}
    </div>
  );
};

export default LogViewer;
