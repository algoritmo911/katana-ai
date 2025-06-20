import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import { Paper, Typography, Box, TextField, Button, Grid, Alert } from '@mui/material';
import { toast } from 'react-toastify';

const SOCKET_SERVER_URL = 'http://localhost:5050';

const CommandSender = () => {
    const [action, setAction] = useState('');
    const [parameters, setParameters] = useState('{}');
    // Response/error state for direct feedback in this component, if any, is handled by toast mostly now
    // const [response, setResponse] = useState(null);
    // const [error, setError] = useState(null); // Use toast for most errors

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
                toast.success(`Command "${data.command_id || action}" sent successfully: ${data.message}`);
            } else {
                toast.error(`Command "${action}" failed: ${data.message}`);
            }
        });

        socketRef.current.on('connect_error', (err) => {
            console.error('CommandSender: WebSocket Connection Error:', err);
            toast.error('CommandSender: Failed to connect to WebSocket server.');
        });

        socketRef.current.on('disconnect', (reason) => {
            console.log('CommandSender: Disconnected from WebSocket server:', reason);
        });

        return () => {
            if (socketRef.current) {
                socketRef.current.disconnect();
            }
        };
    }, [action]); // Added action to dependency array for toast message context

    const handleSendCommand = () => {
        if (!action.trim()) {
            toast.error('Action cannot be empty.');
            return;
        }
        try {
            JSON.parse(parameters);
        } catch (e) {
            toast.error('Parameters field must contain valid JSON.');
            return;
        }

        console.log(`CommandSender: Sending command: Action - ${action}, Params - ${parameters}`);
        socketRef.current.emit('send_command_to_katana', { action, parameters });
        // Clear action after sending? Optional.
        // setAction('');
        // setParameters('{}');
    };

    return (
        <Paper elevation={3} sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom sx={{ mb: 2 }}>Send Custom Command</Typography>
            <Grid container spacing={2} alignItems="flex-start">
                <Grid item xs={12} sm={4}> {/* Ensure xs={12} for stacking */}
                    <TextField
                        label="Action"
                        value={action}
                        onChange={(e) => setAction(e.target.value)}
                        fullWidth
                        variant="outlined"
                        size="small"
                    />
                </Grid>
                <Grid item xs={12} sm={5}> {/* Ensure xs={12} for stacking */}
                    <TextField
                        label="Parameters (JSON format)"
                        value={parameters}
                        onChange={(e) => setParameters(e.target.value)}
                        fullWidth
                        multiline
                        minRows={1}
                        variant="outlined"
                        size="small"
                        helperText='Example: {"key": "value"}'
                    />
                </Grid>
                <Grid item xs={12} sm={3} sx={{ display: 'flex', alignItems: 'stretch', height: '100%' }}> {/* Ensure xs={12} and full height for button */}
                    <Button
                        variant="contained"
                        color="primary"
                        onClick={handleSendCommand}
                        disabled={!socketRef.current || !socketRef.current.connected}
                        fullWidth
                        size="medium" // Ensure button is not too small
                    >
                        Send Command
                    </Button>
                </Grid>
            </Grid>
            {/* Removed local Alert for response/error as toasts are now primary for this component */}
        </Paper>
    );
};

export default CommandSender;
