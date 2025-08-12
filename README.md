# Katana CLI

`katana-cli` is a command-line interface designed to streamline development workflows for services running in Kubernetes. Its primary goal is to bridge the gap between local development and remote cloud environments.

## Feature: Telepresence Integration

The core feature of `katana-cli` is its deep integration with **Telepresence**. This allows developers to "teleport" their local development process into a remote Kubernetes cluster. You can intercept traffic meant for a service in the cloud and redirect it to your local machine, allowing you to test your code with real traffic and against live backend services.

### How It Works

The CLI automates the process of connecting to a cluster, intercepting a service, and tearing down the connection.

---

### **`katana connect`**

Establishes a connection to a remote cluster and intercepts a service.

**Usage:**
```bash
katana connect <environment> --service <service-name> --port <local-port>
```

-   `<environment>`: The target environment (e.g., `staging`, `dev`). This is used for context in output messages.
-   `--service <service-name>`: **(Required)** The name of the Kubernetes service you want to intercept.
-   `--port <local-port>`: **(Required)** The port on which your local service is running.

**Example:**
```bash
# Intercept 'auth-service' in the staging cluster, which is running locally on port 8080
katana connect staging --service auth-service --port 8080
```
This command will first run `telepresence connect` and then `telepresence intercept`, handing your terminal over to an interactive Telepresence session.

---

### **`katana disconnect`**

Removes an intercept and terminates the connection to the cluster.

**Usage:**
```bash
katana disconnect <service-name>
```

-   `<service-name>`: The name of the service you previously intercepted.

**Example:**
```bash
katana disconnect auth-service
```
This command will run `telepresence leave` to stop the intercept and `telepresence quit` to shut down the connection daemon.
