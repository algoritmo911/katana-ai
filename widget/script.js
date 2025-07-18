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

sendCommandButton.addEventListener('click', async () => {
    const command = commandInput.value;
    if (command) {
        const response = await fetch("http://localhost:5000/command", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ command })
        });
        const data = await response.json();
        console.log(data);
        commandInput.value = '';
    }
});
