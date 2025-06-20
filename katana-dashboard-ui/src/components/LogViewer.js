import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import { List, ListItem, ListItemText, Typography, Paper, Box } from '@mui/material';

const SOCKET_SERVER_URL = 'http://localhost:5050'; // Ensure this matches your backend server port

const LogViewer = () => {
    const [logs, setLogs] = useState([]);
    const socketRef = useRef(null);
    const scrollRef = useRef(null);

    useEffect(() => {
        // Connect to WebSocket server
        socketRef.current = io(SOCKET_SERVER_URL, {
            transports: ['websocket'] // Explicitly use websockets
        });

        console.log('Attempting to connect to WebSocket server...');

        socketRef.current.on('connect', () => {
            console.log('Connected to WebSocket server!');
            // Request initial data once connected
            socketRef.current.emit('request_initial_data');
            console.log('Requested initial data.');
        });

        socketRef.current.on('initial_data', (data) => {
            console.log('Received initial_data:', data);
            if (data && data.logs) {
                setLogs(data.logs);
            }
        });

        socketRef.current.on('new_log_entries', (data) => {
            console.log('Received new_log_entries:', data);
            if (data && data.logs) {
                setLogs(prevLogs => [...prevLogs, ...data.logs]);
            }
        });

        socketRef.current.on('connect_error', (err) => {
            console.error('WebSocket Connection Error:', err);
        });

        socketRef.current.on('disconnect', (reason) => {
            console.log('Disconnected from WebSocket server:', reason);
        });

        // Cleanup on component unmount
        return () => {
            if (socketRef.current) {
                console.log('Disconnecting WebSocket...');
                socketRef.current.disconnect();
            }
        };
    }, []);

    useEffect(() => {
        // Auto-scroll to the bottom
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <Paper elevation={3} sx={{ height: '400px', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ p: 2, borderBottom: '1px solid #ddd' }}>
                <Typography variant="h6">Katana Event Log</Typography>
            </Box>
            <Box ref={scrollRef} sx={{ flexGrow: 1, overflowY: 'auto', p: 2, whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                {logs.length === 0 && <Typography>No logs yet. Waiting for connection...</Typography>}
                {logs.map((log, index) => (
                    <div key={index}>{log}</div>
                ))}
            </Box>
        </Paper>
    );
};

export default LogViewer;
