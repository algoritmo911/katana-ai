# Katana AI CLI

The ultimate tool for managing your AI assistant.

## Installation

It is recommended to install the Katana AI CLI using `pipx`.

```bash
pipx install git+https://github.com/algoritmo911/katana-ai.git
```

## Usage

```
katana [OPTIONS] COMMAND [ARGS]...
```

### Options

*   `--auth-token TEXT`: Authentication token.
*   `--help`: Show this message and exit.

### Commands

*   `cancel`: Cancel a task by its ID.
*   `config`: Manage the CLI configuration.
*   `flush`: Flush the system.
*   `history`: Show the command history.
*   `log`: Show the logs.
*   `ping`: Ping the Katana AI.
*   `queue`: Show the command queue.
*   `status`: Get the status of the Katana AI.

### `config` command

The `config` command has two subcommands:

*   `set KEY VALUE`: Set a configuration key-value pair.
*   `show`: Show the current configuration.

## Examples

### Get the status of the Katana AI

```bash
katana status
```

### Get the status in JSON format

```bash
katana status --json
```

### Set the API endpoint

```bash
katana config set endpoint http://localhost:3000
```