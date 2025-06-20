import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import { Paper, Typography, Box, Button, Alert, Stack } from '@mui/material';
import { toast } from 'react-toastify'; // Import toast

const SOCKET_SERVER_URL = 'http://localhost:5050';

const KatanaControls = () => {
    const [pingResponse, setPingResponse] = useState(null);
    // reloadResponse state is no longer needed as we'll use toasts
    const [error, setError] = useState(null); // For connection errors or other non-toast errors
    const socketRef = useRef(null);

    useEffect(() => {
        socketRef.current = io(SOCKET_SERVER_URL, {
            transports: ['websocket']
        });

        socketRef.current.on('connect', () => {
            console.log('KatanaControls: Connected to WebSocket server!');
            setError(null);
        });

        socketRef.current.on('agent_response', (data) => {
            console.log('KatanaControls: Received agent_response:', data);
            if (data.status === 'success') {
                if (data.type === 'ping_response') {
                    setPingResponse(data.data);
                    setError(null);
                } else if (data.type === 'reload_response') {
                    toast.success(data.message || 'Reload command processed successfully by backend.');
                    setError(null);
                } else {
                    // Generic success toast for other types if needed
                    toast.info(data.message || JSON.stringify(data.data));
                }
            } else {
                // For agent_response errors, use toast
                toast.error(data.message || 'An unknown error occurred in agent response.');
                setPingResponse(null);
            }
        });

        socketRef.current.on('command_response', (data) => {
            // This is for the generic 'send_command_to_katana' from CommandSender,
            // KatanaControls primarily uses specific events now.
            // If KatanaControls were to use generic send, it would show toast here.
            console.log('KatanaControls: Received command_response (for generic commands):', data);
            // if (data.success) {
            // toast.success(data.message);
            // } else {
            // toast.error(data.message);
            // }
        });

        socketRef.current.on('connect_error', (err) => {
            console.error('KatanaControls: WebSocket Connection Error:', err);
            setError('Failed to connect to WebSocket server for controls. Toast will show specific errors.');
            toast.error(`Connection Error: ${err.message || 'Cannot connect to server'}`);
        });

        socketRef.current.on('disconnect', (reason) => {
            console.log('KatanaControls: Disconnected from WebSocket server:', reason);
            // toast.warn('Disconnected from server.'); // Socket.IO handles reconnects
        });

        return () => {
            if (socketRef.current) {
                socketRef.current.disconnect();
            }
        };
    }, []);

    const handlePing = () => {
        if (!socketRef.current || !socketRef.current.connected) {
            toast.error('Not connected to server.');
            return;
        }
        setError(null);
        setPingResponse(null);
        console.log('KatanaControls: Emitting ping_agent');
        socketRef.current.emit('ping_agent', { data: 'ping_payload_if_any' });
    };

    const handleReloadSettings = () => {
        if (!socketRef.current || !socketRef.current.connected) {
            toast.error('Not connected to server.');
            return;
        }

        if (window.confirm('Are you sure you want to send the "Reload Core Settings" command to the agent?')) {
            setError(null);
            setPingResponse(null);
            console.log('KatanaControls: Emitting reload_settings_command');
            socketRef.current.emit('reload_settings_command', { data: 'reload_payload_if_any' });
        } else {
            toast.info('Reload settings command cancelled.');
        }
    };

    return (
        <Paper elevation={3} sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Katana Agent Controls</Typography>
            <Stack spacing={2} direction={{ xs: 'column', sm: 'row' }} sx={{ mb: 2 }}>
                <Button
                    variant="outlined"
                    onClick={handlePing}
                    disabled={!socketRef.current || !socketRef.current.connected}
                >
                    Ping Agent
                </Button>
                <Button
                    variant="outlined"
                    onClick={handleReloadSettings}
                    disabled={!socketRef.current || !socketRef.current.connected}
                >
                    Reload Core Settings
                </Button>
            </Stack>

            {error && <Alert severity="warning" sx={{ mt: 2 }}>{error}</Alert>} {/* For persistent errors like initial connection failure */}

            {pingResponse && (
                <Alert severity="info" sx={{ mt: 2, whiteSpace: 'pre-wrap' }}>
                    <Typography variant="subtitle2">Ping Response:</Typography>
                    {JSON.stringify(pingResponse, null, 2)}
                </Alert>
            )}
            {/* reloadResponse Alert is removed, toasts are used instead */}
        </Paper>
    );
};

export default KatanaControls;
