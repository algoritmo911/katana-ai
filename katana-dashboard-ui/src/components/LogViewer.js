import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import { Typography, Paper, Box, List, ListItem, ListItemText } from '@mui/material';

const SOCKET_SERVER_URL = 'http://localhost:5050';

const LogViewer = () => {
    const [logs, setLogs] = useState([]);
    const socketRef = useRef(null);
    const scrollBoxRef = useRef(null); // For the scrollable Box

    useEffect(() => {
        socketRef.current = io(SOCKET_SERVER_URL, {
            transports: ['websocket']
        });

        console.log('LogViewer: Attempting to connect...');

        socketRef.current.on('connect', () => {
            console.log('LogViewer: Connected!');
            socketRef.current.emit('request_initial_data');
        });

        socketRef.current.on('initial_data', (data) => {
            console.log('LogViewer: Received initial_data logs:', data && data.logs ? data.logs.length : 0);
            if (data && data.logs) {
                setLogs(data.logs);
            }
        });

        socketRef.current.on('new_log_entries', (data) => {
            console.log('LogViewer: Received new_log_entries:', data && data.logs ? data.logs.length : 0);
            if (data && data.logs) {
                setLogs(prevLogs => [...prevLogs, ...data.logs]);
            }
        });

        socketRef.current.on('connect_error', (err) => {
            console.error('LogViewer: WebSocket Connection Error:', err);
        });

        socketRef.current.on('disconnect', (reason) => {
            console.log('LogViewer: Disconnected:', reason);
        });

        return () => {
            if (socketRef.current) {
                socketRef.current.disconnect();
            }
        };
    }, []);

    useEffect(() => {
        // Auto-scroll to the bottom
        if (scrollBoxRef.current) {
            scrollBoxRef.current.scrollTop = scrollBoxRef.current.scrollHeight;
        }
    }, [logs]);

    return (
        <Paper elevation={3} sx={{ display: 'flex', flexDirection: 'column' }}>
            <Box sx={{ p: 2, borderBottom: '1px solid #ddd' }}>
                <Typography variant="h6">Katana Event Log</Typography>
            </Box>
            <Box
                ref={scrollBoxRef}
                sx={{
                    height: '400px', // Fixed height for scrollability
                    flexGrow: 1,
                    overflowY: 'auto',
                    p: 1, // Reduced padding for denser logs if preferred
                    fontFamily: 'monospace',
                    fontSize: '0.8rem', // Slightly smaller for more content
                    bgcolor: 'grey.50' // Light background for the log area
                }}
            >
                {logs.length === 0 ? (
                    <Typography sx={{ p: 1, color: 'text.secondary' }}>No logs yet. Waiting for connection...</Typography>
                ) : (
                    <List dense disablePadding>
                        {logs.map((log, index) => (
                            <ListItem
                                key={index}
                                sx={{
                                    py: 0.25, // Reduced vertical padding
                                    px: 1,
                                    wordBreak: 'break-all',
                                    // Example: alternating background, uncomment if desired
                                    // bgcolor: index % 2 ? 'grey.100' : 'transparent',
                                }}
                            >
                                <ListItemText
                                    primary={log}
                                    primaryTypographyProps={{ sx: { fontFamily: 'monospace', fontSize: 'inherit' } }}
                                />
                            </ListItem>
                        ))}
                    </List>
                )}
            </Box>
        </Paper>
    );
};

export default LogViewer;
