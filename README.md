# Remote SSH MCP Server

An implementation of an MCP (Message Control Protocol) server that accesses a remote file system through SSH. This project provides functionality to connect to remote servers via SSH and manage their file systems.

## Features

- Remote file system access via SSH
- Remote file reading/writing
- Remote directory listing
- File searching
- Remote command execution
- MCP protocol support

## Requirements

- Python 3.7+
- paramiko library
- mcp package

## Installation

Install the required libraries:
```bash
pip install paramiko mcp
```

## Usage

### Running from the Command Line

```bash
python main.py --hostname example.com --port 22 --username user --password pass --base-path /home/user
```

### Using a Configuration File

1. Create an SSH configuration file (e.g., `ssh_config.json`):

```json
{
  "hostname": "example.com",
  "port": 22,
  "username": "your_username",
  "password": "your_password",
  "base_path": "/home/your_username"
}
```

2. Run using the configuration file:

```bash
python main.py --config ssh_config.json
```

### MCP Configuration File

To integrate the MCP server with other MCP clients, you can use a configuration file in the following format:

```json
{
  "mcpServers": {
    "remote-ssh-file-server": {
      "command": "python",
      "args": ["main.py", "--config", "ssh_config.json"],
      "cwd": "/path/to/py-mcp-ssh"
    }
  }
}
```

## Command Line Options

| Option | Description |
|------|------|
| `--config` | Path to SSH configuration JSON file |
| `--hostname` | SSH server hostname |
| `--port` | SSH server port (default: 22) |
| `--username` | SSH username |
| `--password` | SSH password |
| `--key-file` | Path to SSH key file |
| `--base-path` | Base working directory (default: /) |

## MCP API List

| API Name | Description |
|----------|------|
| `remote_read_file` | Read a remote file |
| `remote_write_file` | Write to a remote file |
| `remote_list_directory` | List the contents of a remote directory |
| `remote_search_files` | Search for files on the remote server |
| `remote_execute_command` | Execute a command on the remote server |

## Security Considerations

- Using key file authentication instead of password is better for security.
- Avoid storing passwords as plaintext in configuration files.
- Restrict `base_path` to a specific user directory instead of root (/) to enhance security.