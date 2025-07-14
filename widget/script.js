const widget = document.getElementById('katana-widget');
const closeButton = document.getElementById('close-button');
const commandInput = document.getElementById('command-input');
const sendCommandButton = document.getElementById('send-command-button');

function showWidget() {
    widget.style.display = 'block';
}

function hideWidget() {
    widget.style.display = 'none';
}

closeButton.addEventListener('click', hideWidget);

// Show the widget after a delay
setTimeout(showWidget, 2000);

sendCommandButton.addEventListener('click', () => {
    const command = commandInput.value;
    if (command) {
        // Later, we'll send the command to the backend here.
        console.log(`Sending command: ${command}`);
        commandInput.value = '';
    }
});
