import React from 'react';
import LogViewer from '../components/LogViewer';
import LogConfiguration from '../components/LogConfiguration';

const LogsPage: React.FC = () => {
  const pageStyle: React.CSSProperties = {
    padding: '20px',
    maxWidth: '1400px', // Allow wider content for logs
    margin: '0 auto',
    fontFamily: 'Arial, sans-serif',
  };

  const sectionStyle: React.CSSProperties = {
    marginBottom: '40px', // Increased margin for better separation
    padding: '20px',
    backgroundColor: '#fff', // Give sections a background
    border: '1px solid #ddd',
    borderRadius: '8px',
    boxShadow: '0 2px 5px rgba(0,0,0,0.05)',
  };

  const headingStyle: React.CSSProperties = {
    marginTop: '0',
    marginBottom: '20px',
    color: '#333',
    borderBottom: '2px solid #eee',
    paddingBottom: '10px',
  };

  const mainHeadingStyle: React.CSSProperties = {
    textAlign: 'center',
    marginBottom: '30px',
    color: '#2c3e50',
  }

  return (
    <div className="logs-page" style={pageStyle}>
      <h1 style={mainHeadingStyle}>Application Logs & Configuration</h1>

      <section style={sectionStyle}>
        <h2 style={headingStyle}>Log Configuration</h2>
        <LogConfiguration />
      </section>

      <section style={sectionStyle}>
        <h2 style={headingStyle}>Log Viewer</h2>
        <LogViewer />
      </section>
    </div>
  );
};

export default LogsPage;
