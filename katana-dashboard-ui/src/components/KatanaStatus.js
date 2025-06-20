import React, { useState, useEffect, useRef } from 'react';
import io from 'socket.io-client';
import {
    Paper, Typography, Box, Grid, Card, CardContent,
    Chip, Button, IconButton
} from '@mui/material';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { toast } from 'react-toastify';

const SOCKET_SERVER_URL = 'http://localhost:5050';

const KatanaStatus = () => {
    const [isConnected, setIsConnected] = useState(false);
    const [memory, setMemory] = useState(null);
    const [commandsInfo, setCommandsInfo] = useState({ pending: 0, processed: 0, total: 0 });
    const [agentConfig, setAgentConfig] = useState(null);
    const [serverUptime, setServerUptime] = useState(null);
    const [lastUpdated, setLastUpdated] = useState(null);
    const [pingData, setPingData] = useState(null); // To store all ping response data

    const socketRef = useRef(null);

    useEffect(() => {
        socketRef.current = io(SOCKET_SERVER_URL, {
            transports: ['websocket'],
            reconnectionAttempts: 5, // Try to reconnect a few times
        });

        console.log('KatanaStatus: Attempting to connect...');

        socketRef.current.on('connect', () => {
            console.log('KatanaStatus: Connected!');
            setIsConnected(true);
            setLastUpdated(new Date().toLocaleTimeString());
            socketRef.current.emit('request_initial_data');
            console.log('KatanaStatus: Requested initial data on connect.');
        });

        socketRef.current.on('disconnect', (reason) => {
            console.log('KatanaStatus: Disconnected:', reason);
            setIsConnected(false);
            setLastUpdated(new Date().toLocaleTimeString());
            if (reason === 'io server disconnect') {
                // The server intentionally disconnected the socket
                toast.warn('Disconnected by server.');
            } else {
                // Else, probably a network issue, socket.io will try to reconnect if configured
                toast.info('Disconnected. Attempting to reconnect...');
            }
        });

        socketRef.current.on('connect_error', (err) => {
            console.error('KatanaStatus: Connection Error:', err);
            setIsConnected(false);
            setLastUpdated(new Date().toLocaleTimeString());
            // toast.error(`Connection Error: ${err.message}. Please check server.`);
        });

        socketRef.current.on('initial_data', (data) => {
            console.log('KatanaStatus: Received initial_data:', data);
            if (data) {
                setMemory(data.memory || {});
                if (data.memory && data.memory.katana_config) {
                    setAgentConfig(data.memory.katana_config);
                } else {
                    // If katana_config is not present, try to get it from top-level memory keys
                    // This is a fallback, ideally katana_config is a specific key
                    const { logs, commands, ...potentialConfig } = data.memory || {};
                    if (Object.keys(potentialConfig).length > 0 && !agentConfig) {
                         // setAgentConfig(potentialConfig); // Decided against this for now to keep it clean
                    }
                }
                const cmds = data.commands || [];
                const pending = cmds.filter(cmd => !(cmd.processed || cmd.status_after_execution === 'success' || cmd.status_after_execution === 'failed')).length;
                setCommandsInfo({ pending, processed: cmds.length - pending, total: cmds.length });
                setLastUpdated(new Date().toLocaleTimeString());
            }
        });

        socketRef.current.on('agent_response', (response) => {
            console.log('KatanaStatus: Received agent_response:', response);
            if (response.type === 'ping_response' && response.data) {
                setServerUptime(response.data.server_uptime_seconds);
                setPingData(response.data); // Store all ping data
                setLastUpdated(new Date().toLocaleTimeString());
            }
            // Potentially handle other agent_response types if they update status
        });

        // Example: listen for memory updates if backend pushes them
        // socketRef.current.on('memory_updated', (newMemory) => {
        //     setMemory(newMemory);
        //     if (newMemory && newMemory.katana_config) {
        //         setAgentConfig(newMemory.katana_config);
        //     }
        //     setLastUpdated(new Date().toLocaleTimeString());
        // });


        // Cleanup
        return () => {
            if (socketRef.current) {
                console.log('KatanaStatus: Disconnecting WebSocket on component unmount.');
                socketRef.current.disconnect();
            }
        };
    }, []); // Empty dependency array means this effect runs once on mount and cleans up on unmount

    const handleCopyConfig = () => {
        if (agentConfig) {
            const configString = JSON.stringify(agentConfig, null, 2);
            navigator.clipboard.writeText(configString)
                .then(() => toast.success('Agent config copied to clipboard!'))
                .catch(err => toast.error('Failed to copy config.'));
        }
    };

    const formatUptime = (totalSeconds) => {
        if (totalSeconds === null || totalSeconds === undefined) return 'N/A';
        const days = Math.floor(totalSeconds / (3600 * 24));
        const hours = Math.floor((totalSeconds % (3600 * 24)) / 3600);
        const minutes = Math.floor((totalSeconds % 3600) / 60);
        const seconds = Math.floor(totalSeconds % 60);
        return `${days}d ${hours}h ${minutes}m ${seconds}s`;
    };

    return (
        <Paper elevation={3} sx={{ p: 2 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
                <Typography variant="h6">Katana System Status</Typography>
                <Chip
                    label={isConnected ? 'Connected' : 'Disconnected'}
                    color={isConnected ? 'success' : 'error'}
                    size="small"
                />
            </Box>
            <Typography variant="caption" display="block" gutterBottom>
                Last updated: {lastUpdated || 'N/A'}
            </Typography>

            <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                        <CardContent>
                            <Typography variant="subtitle1" gutterBottom>Agent Info</Typography>
                            <Typography variant="body2">Version: {pingData?.agent_version || 'N/A'}</Typography>
                            <Typography variant="body2">Server Uptime: {formatUptime(serverUptime)}</Typography>
                            {pingData?.process_metrics && (
                                <>
                                  <Typography variant="body2">CPU Usage: {pingData.process_metrics.cpu_percent?.toFixed(2)}%</Typography>
                                  <Typography variant="body2">Memory (RSS): {pingData.process_metrics.rss_mb?.toFixed(2)} MB</Typography>
                                </>
                            )}
                        </CardContent>
                    </Card>
                </Grid>
                <Grid item xs={12} md={6}>
                    <Card variant="outlined">
                        <CardContent>
                            <Typography variant="subtitle1" gutterBottom>Command Queue</Typography>
                            <Typography variant="body2">Pending: {commandsInfo.pending}</Typography>
                            <Typography variant="body2">Processed (session view): {commandsInfo.processed}</Typography>
                            <Typography variant="body2">Total (session view): {commandsInfo.total}</Typography>
                        </CardContent>
                    </Card>
                </Grid>
                {agentConfig && (
                    <Grid item xs={12}>
                        <Card variant="outlined">
                            <CardContent>
                                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                    <Typography variant="subtitle1" gutterBottom>Agent Configuration (from memory)</Typography>
                                    <IconButton onClick={handleCopyConfig} size="small" title="Copy config">
                                        <ContentCopyIcon fontSize="small"/>
                                    </IconButton>
                                </Box>
                                <Box sx={{ maxHeight: '200px', overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all', bgcolor: 'grey.100', p: 1, borderRadius: 1, fontFamily: 'monospace', fontSize: '0.8rem' }}>
                                    {JSON.stringify(agentConfig, null, 2)}
                                </Box>
                            </CardContent>
                        </Card>
                    </Grid>
                )}
                 {/* Raw Memory display - can be large */}
                 {/* <Grid item xs={12}>
                    <Card variant="outlined">
                        <CardContent>
                            <Typography variant="subtitle1" gutterBottom>Full Memory State</Typography>
                            <Box sx={{ maxHeight: '150px', overflowY: 'auto', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: 'monospace', fontSize: '0.75rem', bgcolor: 'grey.50', p:1 }}>
                                {memory ? JSON.stringify(memory, null, 2) : 'Loading memory...'}
                            </Box>
                        </CardContent>
                    </Card>
                </Grid> */}
            </Grid>
        </Paper>
    );
};

export default KatanaStatus;
