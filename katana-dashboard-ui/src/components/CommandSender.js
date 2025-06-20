import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import { Paper, Typography, Box, TextField, Button, Grid, Alert } from '@mui/material';

const SOCKET_SERVER_URL = 'http://localhost:5050';

const CommandSender = () => {
    const [action, setAction] = useState('');
    const [parameters, setParameters] = useState('{}'); // Parameters as JSON string
    const [response, setResponse] = useState(null);
    const [error, setError] = useState(null);
    const socketRef = useRef(null);

    useEffect(() => {
        socketRef.current = io(SOCKET_SERVER_URL, {
            transports: ['websocket']
        });

        socketRef.current.on('connect', () => {
            console.log('CommandSender: Connected to WebSocket server!');
        });

        socketRef.current.on('command_response', (data) => {
            console.log('CommandSender: Received command_response:', data);
            if (data.success) {
                setResponse(data.message);
                setError(null);
            } else {
                setError(data.message);
                setResponse(null);
            }
        });

        socketRef.current.on('connect_error', (err) => {
            console.error('CommandSender: WebSocket Connection Error:', err);
            setError('Failed to connect to WebSocket server for sending commands.');
        });

        socketRef.current.on('disconnect', (reason) => {
            console.log('CommandSender: Disconnected from WebSocket server:', reason);
        });

        return () => {
            if (socketRef.current) {
                socketRef.current.disconnect();
            }
        };
    }, []);

    const handleSendCommand = () => {
        if (!action.trim()) {
            setError('Action cannot be empty.');
            return;
        }
        try {
            // Validate JSON format for parameters
            JSON.parse(parameters);
        } catch (e) {
            setError('Parameters field must contain valid JSON.');
            return;
        }

        setError(null);
        setResponse(null);
        console.log(`CommandSender: Sending command: Action - ${action}, Params - ${parameters}`);
        socketRef.current.emit('send_command_to_katana', { action, parameters });
    };

    return (
        <Paper elevation={3} sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Send Command to Katana</Typography>
            <Grid container spacing={2} alignItems="flex-start">
                <Grid item xs={12} sm={4}>
                    <TextField
                        label="Action"
                        value={action}
                        onChange={(e) => setAction(e.target.value)}
                        fullWidth
                        variant="outlined"
                        size="small"
                    />
                </Grid>
                <Grid item xs={12} sm={5}>
                    <TextField
                        label="Parameters (JSON format)"
                        value={parameters}
                        onChange={(e) => setParameters(e.target.value)}
                        fullWidth
                        multiline
                        minRows={1}
                        variant="outlined"
                        size="small"
                        helperText='Example: {"key": "value", "count": 1}'
                    />
                </Grid>
                <Grid item xs={12} sm={3} sx={{ display: 'flex', alignItems: 'center' }}>
                    <Button
                        variant="contained"
                        color="primary"
                        onClick={handleSendCommand}
                        disabled={!socketRef.current || !socketRef.current.connected}
                        fullWidth
                    >
                        Send Command
                    </Button>
                </Grid>
            </Grid>
            {response && <Alert severity="success" sx={{ mt: 2 }}>{response}</Alert>}
            {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
        </Paper>
    );
};

export default CommandSender;
