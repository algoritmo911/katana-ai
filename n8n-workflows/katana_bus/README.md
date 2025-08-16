# Katana Bus - n8n Workflows

This repository stores the n8n workflows that serve as Katana's "Action Bus," as outlined in the Kusanagi-v1.0 directive.

Katana uses this bus to safely execute actions in external systems. The core `katana-ai` engine sends standardized jobs to n8n, which contains the necessary credentials and logic to interact with third-party services like GitHub, Slack, and the local operating system.

This separation of concerns ensures that the core AI logic does not need to store sensitive API keys.
