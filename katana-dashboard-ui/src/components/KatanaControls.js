import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import { Paper, Typography, Box, Button, Grid, Alert, Stack } from '@mui/material';

const SOCKET_SERVER_URL = 'http://localhost:5050';

const KatanaControls = () => {
    const [response, setResponse] = useState(null);
    const [error, setError] = useState(null);
    const socketRef = useRef(null);

    useEffect(() => {
        socketRef.current = io(SOCKET_SERVER_URL, {
            transports: ['websocket']
        });

        socketRef.current.on('connect', () => {
            console.log('KatanaControls: Connected to WebSocket server!');
        });

        socketRef.current.on('command_response', (data) => {
            console.log('KatanaControls: Received command_response:', data);
            if (data.success) {
                setResponse(`${data.message} (ID: ${data.command_id})`);
                setError(null);
            } else {
                setError(data.message);
                setResponse(null);
            }
        });

        socketRef.current.on('connect_error', (err) => {
            console.error('KatanaControls: WebSocket Connection Error:', err);
            setError('Failed to connect to WebSocket server for sending controls.');
        });

        socketRef.current.on('disconnect', (reason) => {
            console.log('KatanaControls: Disconnected from WebSocket server:', reason);
        });

        return () => {
            if (socketRef.current) {
                socketRef.current.disconnect();
            }
        };
    }, []);

    const sendControlCommand = (action, params = {}) => {
        if (!socketRef.current || !socketRef.current.connected) {
            setError('Not connected to server.');
            return;
        }
        setError(null);
        setResponse(null);
        const command = { action, parameters: JSON.stringify(params) };
        console.log('KatanaControls: Sending control command:', command);
        socketRef.current.emit('send_command_to_katana', command);
    };

    return (
        <Paper elevation={3} sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Katana Agent Controls</Typography>
            <Stack spacing={2} direction={{ xs: 'column', sm: 'row' }}>
                <Button
                    variant="outlined"
                    onClick={() => sendControlCommand('ping_agent')}
                    disabled={!socketRef.current || !socketRef.current.connected}
                >
                    Ping Agent
                </Button>
                <Button
                    variant="outlined"
                    onClick={() => sendControlCommand('get_agent_config')}
                    disabled={!socketRef.current || !socketRef.current.connected}
                >
                    Get Agent Config
                </Button>
                <Button
                    variant="outlined"
                    onClick={() => sendControlCommand('reload_core_settings')}
                    disabled={!socketRef.current || !socketRef.current.connected}
                >
                    Reload Core Settings
                </Button>
            </Stack>
            {response && <Alert severity="success" sx={{ mt: 2 }}>{response}</Alert>}
            {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        </Paper>
    );
};

export default KatanaControls;
