import React from 'react';
import { AppBar, Toolbar, Typography, Container, Box, CssBaseline } from '@mui/material';
import LogViewer from './components/LogViewer';
import KatanaStatus from './components/KatanaStatus';
import CommandSender from './components/CommandSender';
import KatanaControls from './components/KatanaControls'; // <-- New import
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

function App() {
  return (
    <>
      <CssBaseline />
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop={false}
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
      />
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            Katana AI Dashboard
          </Typography>
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ my: 2 }}>
          <Typography variant="h4" component="h1" gutterBottom>
            Welcome to Katana Dashboard
          </Typography>
        </Box>

        {/* Katana Controls Component */}
        <Box sx={{ my: 4 }}>
          <KatanaControls />
        </Box>

        {/* Katana Status Component */}
        <Box sx={{ my: 4 }}>
          <KatanaStatus />
        </Box>

        {/* Command Sender Component */}
        <Box sx={{ my: 4 }}>
          <CommandSender />
        </Box>

        {/* Log Viewer Component */}
        <LogViewer />

      </Container>
    </>
  );
}

export default App;
