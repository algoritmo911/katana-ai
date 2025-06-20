import React, { useState, useEffect, useCallback, ChangeEvent } from 'react';

interface LogStatus {
  level: string;
  log_file: string;
}

const LogConfiguration: React.FC = () => {
  const [currentStatus, setCurrentStatus] = useState<LogStatus | null>(null);
  const [selectedLevel, setSelectedLevel] = useState<string>("");
  const [isLoadingStatus, setIsLoadingStatus] = useState<boolean>(true);
  const [isUpdatingLevel, setIsUpdatingLevel] = useState<boolean>(false);
  const [statusError, setStatusError] = useState<string | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [updateSuccessMessage, setUpdateSuccessMessage] = useState<string | null>(null);

  const logLevels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"];

  const fetchLogStatus = useCallback(async () => {
    setIsLoadingStatus(true);
    setStatusError(null);
    try {
      const response = await fetch('/api/logs/status');
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error fetching log status: ${response.statusText}`);
      }
      const data: LogStatus = await response.json();
      setCurrentStatus(data);
      setSelectedLevel(data.level); // Initialize selectedLevel with current status
    } catch (err) {
      if (err instanceof Error) {
        setStatusError(err.message);
      } else {
        setStatusError('An unknown error occurred while fetching log status.');
      }
    } finally {
      setIsLoadingStatus(false);
    }
  }, []);

  useEffect(() => {
    fetchLogStatus();
  }, [fetchLogStatus]);

  const handleUpdateLogLevel = async () => {
    if (!selectedLevel || selectedLevel === currentStatus?.level) {
      setUpdateError("Please select a different log level to update.");
      return;
    }

    setIsUpdatingLevel(true);
    setUpdateError(null);
    setUpdateSuccessMessage(null);

    try {
      const response = await fetch('/api/logs/level', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ level: selectedLevel }),
      });
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `Error updating log level: ${response.statusText}`);
      }
      const result = await response.json();
      setUpdateSuccessMessage(result.message || "Log level updated successfully!");
      fetchLogStatus(); // Refresh status after successful update
    } catch (err) {
      if (err instanceof Error) {
        setUpdateError(err.message);
      } else {
        setUpdateError('An unknown error occurred while updating log level.');
      }
    } finally {
      setIsUpdatingLevel(false);
    }
  };

  const handleSelectedLevelChange = (event: ChangeEvent<HTMLSelectElement>) => {
    setSelectedLevel(event.target.value);
    // Clear messages when user changes selection, preparing for new action
    setUpdateError(null);
    setUpdateSuccessMessage(null);
  };

  const styles: { [key: string]: React.CSSProperties } = {
    container: {
      fontFamily: 'Arial, sans-serif',
      padding: '20px',
      backgroundColor: '#f9f9f9',
      borderRadius: '8px',
      boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
      maxWidth: '600px',
      margin: '20px auto',
    },
    statusSection: {
      marginBottom: '20px',
      paddingBottom: '10px',
      borderBottom: '1px solid #eee',
    },
    configSection: {
      display: 'flex',
      flexDirection: 'column',
      gap: '10px',
    },
    label: {
      fontWeight: 'bold',
      marginRight: '10px',
      fontSize: '0.95em',
    },
    infoText: {
      color: '#333',
      marginBottom: '5px',
    },
    selectInput: {
      padding: '10px',
      borderRadius: '4px',
      border: '1px solid #ccc',
      marginBottom: '10px',
      fontSize: '1em',
    },
    button: {
      padding: '10px 15px',
      fontSize: '1em',
      cursor: 'pointer',
      backgroundColor: '#007bff',
      color: 'white',
      border: 'none',
      borderRadius: '4px',
      alignSelf: 'flex-start',
    },
    buttonDisabled: {
      backgroundColor: '#ccc',
      cursor: 'not-allowed',
    },
    error: {
      color: 'red',
      marginTop: '10px',
      padding: '8px',
      border: '1px solid red',
      borderRadius: '4px',
      backgroundColor: '#ffe0e0',
    },
    success: {
      color: 'green',
      marginTop: '10px',
      padding: '8px',
      border: '1px solid green',
      borderRadius: '4px',
      backgroundColor: '#e0ffe0',
    },
    loading: {
      fontStyle: 'italic',
      color: '#555',
    }
  };

  return (
    <div style={styles.container}>
      <h3>Log Configuration</h3>

      <div style={styles.statusSection}>
        <h4>Current Status</h4>
        {isLoadingStatus && <p style={styles.loading}>Loading status...</p>}
        {statusError && <p style={styles.error}>Error fetching status: {statusError}</p>}
        {currentStatus && !isLoadingStatus && (
          <>
            <p style={styles.infoText}>
              <span style={styles.label}>Application Log Level:</span> {currentStatus.level}
            </p>
            <p style={styles.infoText}>
              <span style={styles.label}>Log File Path:</span> {currentStatus.log_file}
            </p>
          </>
        )}
      </div>

      <h4>Set Application Log Level</h4>
      <div style={styles.configSection}>
        <label htmlFor="log-level-select" style={styles.label}>New Log Level:</label>
        <select
          id="log-level-select"
          value={selectedLevel}
          onChange={handleSelectedLevelChange}
          style={styles.selectInput}
          disabled={isLoadingStatus} // Disable while initial status is loading
        >
          <option value="" disabled={!currentStatus}>Select level...</option>
          {logLevels.map(level => (
            <option key={level} value={level}>{level}</option>
          ))}
        </select>
        <button
          onClick={handleUpdateLogLevel}
          disabled={isUpdatingLevel || isLoadingStatus || !selectedLevel || selectedLevel === currentStatus?.level}
          style={{
            ...styles.button,
            ...((isUpdatingLevel || isLoadingStatus || !selectedLevel || selectedLevel === currentStatus?.level) ? styles.buttonDisabled : {})
          }}
        >
          {isUpdatingLevel ? 'Updating...' : 'Set Level'}
        </button>
        {updateError && <p style={styles.error}>{updateError}</p>}
        {updateSuccessMessage && <p style={styles.success}>{updateSuccessMessage}</p>}
      </div>
    </div>
  );
};

export default LogConfiguration;
