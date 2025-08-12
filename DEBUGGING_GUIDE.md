# 5-Minute Debugging Guide: `auth-service` in Staging

This guide provides a real-world example of how to use `katana-cli` to debug a service running in a remote Kubernetes cluster by redirecting its traffic to your local machine.

### Prerequisites

1.  **Local Service Code:** You have the source code for the `auth-service` on your machine.
2.  **Local Environment:** Your service can be run locally (e.g., via `go run`, `npm start`, or inside a Docker container).
3.  **Katana CLI:** You have `katana-cli` installed.
4.  **Dependencies:** You have `telepresence` and a configured `kubectl` on your machine.

---

### Step 1: Connect and Intercept Traffic

Open a terminal in the root directory of your `auth-service` project. Run the `katana connect` command, specifying the `staging` environment, the service name (`auth-service`), and the port your local instance will run on (e.g., `8080`).

```bash
katana connect staging --service auth-service --port 8080
```

This command will connect to the cluster and create an interactive Telepresence session. Traffic that would normally go to the `auth-service` in the `staging` cluster is now redirected to your machine.

### Step 2: Run Your Local Service with Cluster Environment

After a successful intercept, Telepresence creates a `.env` file in your current directory. This file contains all the environment variables from the remote `auth-service` pod. To ensure your local instance behaves exactly like the one in the cluster, you must run it with these variables.

**Example using Docker:**
```bash
# Build your local image
docker build -t auth-service:local .

# Run the container, injecting the environment variables from the .env file
docker run --rm -it -p 8080:8080 --env-file=.env auth-service:local
```

**Example using Node.js:**
```bash
# If you are using a library like `dotenv`, it will pick up the .env file automatically.
npm start
```

### Step 3: Debug Live

Your local `auth-service` is now receiving live traffic from the `staging` environment.

-   **Set Breakpoints:** Place breakpoints in your favorite IDE or debugger.
-   **Add Log Statements:** Add `fmt.Println` or `console.log` statements to your code.
-   **Trigger an Action:** Go to the web interface for the `staging` environment and perform an action that calls the `auth-service` (e.g., log in, view a profile).

You will see the breakpoints hit or the log messages appear in your local terminal, allowing you to inspect real requests and debug in a live environment.

### Step 4: Disconnect

Once you are finished debugging, press `Ctrl+C` in the `katana connect` terminal to end the intercept. Then, to fully clean up the connection, run:

```bash
katana disconnect auth-service
```

This removes the intercept and terminates the Telepresence daemon, returning traffic flow to normal in the cluster.
