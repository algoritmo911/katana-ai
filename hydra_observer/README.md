# Katana Hydra Observer

The Katana Hydra Observer is a service that provides continuous monitoring, telemetry, and event watching for the Katana AI ecosystem.

## Components

-   **Observer:** Listens to the Kafka message bus for logs and stores them in TimescaleDB.
-   **Probes:** Gathers system metrics like CPU, memory, and disk usage.
-   **Watchers:** Watches for specific events or conditions (currently a placeholder).

## Deployment

To deploy the Katana Hydra Observer as a `systemd` service, follow these steps:

1.  **Copy the service file:**
    ```bash
    sudo cp monitoring/katana-hydra-observer.service /etc/systemd/system/
    ```

2.  **Edit the service file:**
    Open the service file and adjust the `User`, `WorkingDirectory`, and `ExecStart` paths to match your environment.
    ```bash
    sudo nano /etc/systemd/system/katana-hydra-observer.service
    ```

3.  **Reload the systemd daemon:**
    ```bash
    sudo systemctl daemon-reload
    ```

4.  **Enable the service to start on boot:**
    ```bash
    sudo systemctl enable katana-hydra-observer.service
    ```

5.  **Start the service:**
    ```bash
    sudo systemctl start katana-hydra-observer.service
    ```

6.  **Check the status of the service:**
    ```bash
    sudo systemctl status katana-hydra-observer.service
    ```

## Log Rotation

The `systemd` service file redirects `stdout` and `stderr` to log files in `/var/log`. It is recommended to set up `logrotate` to manage these log files. Create a new file `/etc/logrotate.d/katana-hydra-observer` with the following content:

```
/var/log/katana-hydra-observer.log
/var/log/katana-hydra-observer.err.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 640 your_user adm
    sharedscripts
}
```

Replace `your_user` with the user that runs the service.
