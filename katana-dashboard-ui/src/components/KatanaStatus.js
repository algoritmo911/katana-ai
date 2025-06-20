import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import { Paper, Typography, Box, Grid, Card, CardContent, List, ListItem, ListItemText } from '@mui/material';

const SOCKET_SERVER_URL = 'http://localhost:5050'; // Ensure this matches your backend server port

const KatanaStatus = () => {
    const [memory, setMemory] = useState(null);
    const [commands, setCommands] = useState([]);
    const socketRef = useRef(null);

    useEffect(() => {
        // Connect to WebSocket server (or reuse existing connection if App.js manages it)
        // For simplicity, this component establishes its own connection for now.
        socketRef.current = io(SOCKET_SERVER_URL, {
            transports: ['websocket']
        });

        console.log('KatanaStatus: Attempting to connect to WebSocket server...');

        socketRef.current.on('connect', () => {
            console.log('KatanaStatus: Connected to WebSocket server!');
            // Request initial data once connected - this will also benefit LogViewer
            // if it's connected around the same time or if backend emits to all.
            // A more robust solution might involve a shared context for socket connection.
            socketRef.current.emit('request_initial_data');
            console.log('KatanaStatus: Requested initial data.');
        });

        socketRef.current.on('initial_data', (data) => {
            console.log('KatanaStatus: Received initial_data:', data);
            if (data) {
                setMemory(data.memory || {});
                setCommands(data.commands || []);
            }
        });

        // Placeholder for future specific status updates if needed
        // socketRef.current.on('katana_status_update', (data) => {
        // console.log('KatanaStatus: Received katana_status_update:', data);
        //     setMemory(data.memory || {});
        //     setCommands(data.commands || []);
        // });

        socketRef.current.on('connect_error', (err) => {
            console.error('KatanaStatus: WebSocket Connection Error:', err);
        });

        socketRef.current.on('disconnect', (reason) => {
            console.log('KatanaStatus: Disconnected from WebSocket server:', reason);
        });

        // Cleanup on component unmount
        return () => {
            if (socketRef.current) {
                console.log('KatanaStatus: Disconnecting WebSocket...');
                socketRef.current.disconnect();
            }
        };
    }, []);

    const pendingCommandsCount = commands.filter(cmd => !(cmd.processed || cmd.status_after_execution === 'success' || cmd.status_after_execution === 'failed')).length;
    const processedCommandsCount = commands.length - pendingCommandsCount;

    return (
        <Paper elevation={3} sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Katana Status</Typography>
            <Grid container spacing={2}>
                <Grid item xs={12} md={6}>
                    <Card>
                        <CardContent>
                            <Typography variant="subtitle1" gutterBottom>Memory State</Typography>
                            {memory ? (
                                <Box sx={{ maxHeight: '200px', overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'monospace', fontSize: '0.875rem' }}>
                                    <pre>{JSON.stringify(memory, null, 2)}</pre>
                                </Box>
                            ) : (
                                <Typography>Loading memory...</Typography>
                            )}
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                    <Card>
                        <CardContent>
                            <Typography variant="subtitle1" gutterBottom>Command Queue</Typography>
                            <Typography>Pending Commands: {pendingCommandsCount}</Typography>
                            <Typography>Processed Commands (in current queue view): {processedCommandsCount}</Typography>
                            <Typography>Total Commands (in current queue view): {commands.length}</Typography>
                            {/* Can add a small list of recent/pending commands here if desired */}
                        </CardContent>
                    </Card>
                </Grid>
            </Grid>
        </Paper>
    );
};

export default KatanaStatus;
