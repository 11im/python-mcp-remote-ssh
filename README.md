# Remote SSH MCP 서버

원격 SSH 서버의 파일 시스템에 접근하는 MCP(Message Control Protocol) 서버 구현입니다. 이 프로젝트는 SSH를 통해 원격 서버에 연결하여 파일 시스템을 관리하는 기능을 제공합니다.

## 기능

- SSH를 통한 원격 파일 시스템 접근
- 원격 파일 읽기/쓰기
- 원격 디렉토리 리스팅
- 파일 검색
- 원격 명령어 실행
- MCP 프로토콜 지원

## 요구사항

- Python 3.7+
- paramiko 라이브러리
- mcp 패키지

## 설치

필요한 라이브러리 설치:
```bash
pip install paramiko mcp
```

## 사용 방법

### 명령행에서 직접 실행

```bash
python main.py --hostname example.com --port 22 --username user --password pass --base-path /home/user
```

### 설정 파일 사용

1. SSH 설정 파일(예: `ssh_config.json`) 생성:

```json
{
  "hostname": "example.com",
  "port": 22,
  "username": "your_username",
  "password": "your_password",
  "base_path": "/home/your_username"
}
```

2. 설정 파일을 사용하여 실행:

```bash
python main.py --config ssh_config.json
```

### MCP 설정 파일

MCP 서버를 다른 MCP 클라이언트와 통합하려면 다음과 같은 형식의 설정 파일을 사용할 수 있습니다:

```json
{
  "mcpServers": {
    "remote-ssh-file-server": {
      "command": "python",
      "args": ["/path/to/py-mcp-ssh/main.py", "--config", "/path/to/py-mcp-ssh/ssh_config.json"]
    }
  }
}
```

## 명령행 옵션

| 옵션 | 설명 |
|------|------|
| `--config` | SSH 설정 JSON 파일 경로 |
| `--hostname` | SSH 서버 호스트명 |
| `--port` | SSH 서버 포트 (기본값: 22) |
| `--username` | SSH 사용자 이름 |
| `--password` | SSH 비밀번호 |
| `--key-file` | SSH 키 파일 경로 |
| `--base-path` | 기본 작업 디렉토리 (기본값: /) |

## MCP API 목록

| API 이름 | 설명 |
|----------|------|
| `remote_read_file` | 원격 파일 읽기 |
| `remote_write_file` | 원격 파일 쓰기 |
| `remote_list_directory` | 원격 디렉토리 내용 나열 |
| `remote_search_files` | 원격 파일 검색 |
| `remote_execute_command` | 원격 서버에서 명령어 실행 |

## 보안 고려사항

- SSH 패스워드 대신 키 파일 인증을 사용하는 것이 보안상 좋습니다.
- 설정 파일에 비밀번호를 평문으로 저장하지 않는 것이 좋습니다.
- `base_path`를 루트(/)가 아닌 특정 사용자 디렉토리로 제한하여 보안을 강화할 수 있습니다.
