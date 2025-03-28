from pathlib import Path
from typing import List, Optional, Dict, Any
import os
import asyncio
import mimetypes
import io
import stat
import argparse
import json
import sys

# MCP 관련 임포트 (pip로 설치된 패키지 사용)
from mcp.server import Server
from mcp.types import Resource, Tool, TextContent

try:
    import paramiko
except ImportError:
    print("paramiko 패키지가 설치되어 있지 않습니다. 다음 명령어로 설치하세요:")
    print("pip install paramiko")
    sys.exit(1)


class RemoteSSHFileSystemManager:
    def __init__(self, hostname: str, port: int = 22, username: str = None, 
                 password: str = None, key_filename: str = None, base_path: str = "/"):
        """
        SSH 파일 시스템 관리자 초기화
        
        Args:
            hostname: SSH 서버 호스트명
            port: SSH 서버 포트 (기본값: 22)
            username: SSH 사용자 이름
            password: SSH 비밀번호 (키 파일 또는 비밀번호 중 하나는 필요)
            key_filename: SSH 키 파일 경로 (키 파일 또는 비밀번호 중 하나는 필요)
            base_path: 기본 작업 디렉토리 (기본값: /)
        """
        self.hostname = hostname
        self.port = port
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.base_path = Path(base_path)
        self._ssh_client = None
        self._sftp_client = None
    
    async def remote_connect(self):
        """SSH 및 SFTP 연결 설정"""
        if self._ssh_client is not None and self._ssh_client.get_transport() and self._ssh_client.get_transport().is_active():
            return

        # 비동기로 SSH 연결 생성
        self._ssh_client = await asyncio.to_thread(paramiko.SSHClient)
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # SSH 서버에 연결
        connect_kwargs = {
            'hostname': self.hostname,
            'port': self.port,
            'username': self.username
        }
        
        if self.password:
            connect_kwargs['password'] = self.password
        if self.key_filename:
            connect_kwargs['key_filename'] = self.key_filename
            
        try:
            await asyncio.to_thread(self._ssh_client.connect, **connect_kwargs)
            # SFTP 클라이언트 생성
            self._sftp_client = await asyncio.to_thread(self._ssh_client.open_sftp)
            print(f"원격 서버 {self.hostname}에 성공적으로 연결되었습니다.")
        except Exception as e:
            print(f"SSH 연결 실패: {str(e)}")
            raise
    
    async def remote_close(self):
        """SSH 및 SFTP 연결 종료"""
        if self._sftp_client:
            await asyncio.to_thread(self._sftp_client.close)
            self._sftp_client = None
            
        if self._ssh_client:
            await asyncio.to_thread(self._ssh_client.close)
            self._ssh_client = None
    
    def _validate_path(self, path: str | Path) -> Path:
        """주어진 경로가 base_path 내에 있는지 확인"""
        if isinstance(path, str):
            # 경로 정규화
            norm_path = os.path.normpath(path)
            full_path = Path(self.base_path) / norm_path if not path.startswith('/') else Path(path)
        else:
            full_path = path
            
        # 기본 경로 하위에 있는지 확인
        base_str = str(self.base_path)
        path_str = str(full_path)
        if not path_str.startswith(base_str):
            raise ValueError(f"Invalid path: Access denied. Path must be within {self.base_path}")
            
        return full_path
    
    async def remote_read_file(self, path: str) -> tuple[str, str]:
        """원격 파일 읽기"""
        await self.remote_connect()
        full_path = self._validate_path(path)
        
        try:
            # 원격 파일을 임시 메모리 객체로 읽기
            with io.BytesIO() as temp_file:
                await asyncio.to_thread(self._sftp_client.getfo, str(full_path), temp_file)
                temp_file.seek(0)
                content = temp_file.read().decode('utf-8')
            
            # MIME 타입 추측
            mime_type, _ = mimetypes.guess_type(str(full_path))
            return content, mime_type or "text/plain"
            
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")
        except PermissionError:
            raise PermissionError(f"Permission denied: {path}")
        except Exception as e:
            raise Exception(f"Error reading file {path}: {str(e)}")
    
    async def remote_write_file(self, path: str, content: str) -> None:
        """원격 파일 쓰기"""
        await self.remote_connect()
        full_path = self._validate_path(path)
        
        try:
            # 원격 파일에 내용 쓰기
            with io.BytesIO(content.encode('utf-8')) as temp_file:
                await asyncio.to_thread(self._sftp_client.putfo, temp_file, str(full_path))
                
        except PermissionError:
            raise PermissionError(f"Permission denied: {path}")
        except Exception as e:
            raise Exception(f"Error writing file {path}: {str(e)}")
    
    async def remote_list_directory(self, path: str = "") -> List[dict]:
        """원격 디렉토리 내용 나열"""
        await self.remote_connect()
        
        if path == "":
            full_path = self.base_path
        else:
            full_path = self._validate_path(path)
        
        try:
            # 원격 디렉토리 내용 가져오기
            attr_list = await asyncio.to_thread(self._sftp_client.listdir_attr, str(full_path))
            
            items = []
            for attr in attr_list:
                is_dir = stat.S_ISDIR(attr.st_mode)
                item_path = str(Path(path) / attr.filename) if path else attr.filename
                
                items.append({
                    "name": attr.filename,
                    "path": item_path,
                    "type": "directory" if is_dir else "file",
                    "size": attr.st_size if not is_dir else None,
                    "permissions": attr.st_mode,
                    "modified": attr.st_mtime
                })
                
            return items
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Directory not found: {path}")
        except PermissionError:
            raise PermissionError(f"Permission denied: {path}")
        except Exception as e:
            raise Exception(f"Error listing directory {path}: {str(e)}")
    
    async def remote_search_files(self, pattern: str, path: str = "") -> List[dict]:
        """원격 파일 검색"""
        base_dir = path if path else str(self.base_path)
        results = []
        
        # find 명령어를 사용하여 원격에서 파일 검색
        command = f"find {base_dir} -name '*{pattern}*' -type f -o -name '*{pattern}*' -type d 2>/dev/null"
        
        await self.remote_connect()
        _, stdout, _ = await asyncio.to_thread(self._ssh_client.exec_command, command)
        output = await asyncio.to_thread(stdout.read)
        file_list = output.decode('utf-8').splitlines()
        
        for file_path in file_list:
            if not file_path.strip():
                continue
                
            try:
                stat_info = await asyncio.to_thread(self._sftp_client.stat, file_path)
                is_dir = stat.S_ISDIR(stat_info.st_mode)
                
                # 경로를 상대 경로로 변환하기 위한 처리
                rel_path = file_path
                if str(self.base_path) != "/":
                    rel_path = file_path[len(str(self.base_path)):].lstrip('/')
                
                results.append({
                    "name": os.path.basename(file_path),
                    "path": rel_path,
                    "type": "directory" if is_dir else "file",
                    "size": stat_info.st_size if not is_dir else None
                })
            except Exception:
                # 권한 문제 등으로 접근할 수 없는 파일은 무시
                pass
                
        return results
    
    async def remote_execute_command(self, command: str) -> tuple[str, str]:
        """원격 서버에서 명령어 실행"""
        await self.remote_connect()
        _, stdout, stderr = await asyncio.to_thread(self._ssh_client.exec_command, command)
        
        out = await asyncio.to_thread(stdout.read)
        err = await asyncio.to_thread(stderr.read)
        
        return out.decode('utf-8'), err.decode('utf-8')


class RemoteSSHFileServer:
    def __init__(self, ssh_config: Dict[str, Any]):
        """
        SSH 파일 서버 초기화
        
        Args:
            ssh_config: SSH 연결 설정 정보 (hostname, port, username, password, key_filename, base_path)
        """
        self.fs = RemoteSSHFileSystemManager(**ssh_config)
        self.server = Server("remote-ssh-file-server")
    
    def setup_handlers(self):
        """MCP 핸들러 설정"""
        @self.server.list_resources()
        async def list_resources() -> list[Resource]:
            items = await self.fs.remote_list_directory()
            return [
                Resource(
                    uri=f"ssh://{self.fs.hostname}/{item['path']}",
                    name=item['name'],
                    mimeType=(
                        "inode/directory" if item['type'] == "directory" 
                        else mimetypes.guess_type(item['name'])[0] or "text/plain"
                    ),
                    description=f"{'Directory' if item['type'] == 'directory' else 'File'}: {item['path']}"
                )
                for item in items
            ]
        
        @self.server.read_resource()
        async def read_resource(uri: str) -> str:
            # ssh://hostname/path 형식의 URI에서 경로 추출
            path = uri.split('/', 3)[3] if uri.count('/') >= 3 else ""
            content, _ = await self.fs.remote_read_file(path)
            return content
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            return [
                Tool(
                    name="remote_write_file",
                    description="원격 파일 작성",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"}
                        },
                        "required": ["path", "content"]
                    }
                ),
                Tool(
                    name="remote_search_files",
                    description="원격 파일 검색",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string"},
                            "path": {"type": "string"}
                        },
                        "required": ["pattern"]
                    }
                ),
                Tool(
                    name="remote_list_directory",
                    description="원격 디렉토리 내용 나열",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {"type": "string"}
                        }
                    }
                ),
                Tool(
                    name="remote_execute_command",
                    description="원격 서버에서 명령어 실행",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {"type": "string"}
                        },
                        "required": ["command"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> list[TextContent]:
            if name == "remote_write_file":
                await self.fs.remote_write_file(
                    arguments["path"],
                    arguments["content"]
                )
                return [TextContent(
                    type="text",
                    text=f"원격 파일 작성 완료: {arguments['path']}"
                )]
                
            elif name == "remote_search_files":
                path = arguments.get("path", "")
                results = await self.fs.remote_search_files(arguments["pattern"], path)
                return [TextContent(
                    type="text",
                    text="\n".join(
                        f"[{r['type']}] {r['path']}"
                        for r in results
                    ) or "일치하는 파일이 없습니다."
                )]
                
            elif name == "remote_list_directory":
                path = arguments.get("path", "")
                results = await self.fs.remote_list_directory(path)
                return [TextContent(
                    type="text",
                    text="\n".join(
                        f"[{r['type']}] {r['path']} ({r['size'] if r['size'] else 'DIR'})"
                        for r in results
                    ) or "디렉토리가 비어있거나 접근할 수 없습니다."
                )]
                
            elif name == "remote_execute_command":
                out, err = await self.fs.remote_execute_command(arguments["command"])
                
                return [
                    TextContent(
                        type="text",
                        text=f"실행 결과:\n{out}\n\n오류(있는 경우):\n{err}"
                    )
                ]
                
            raise ValueError(f"알 수 없는 도구: {name}")


async def main():
    parser = argparse.ArgumentParser(description='SSH를 통한 원격 파일 시스템 MCP 서버')
    parser.add_argument('--config', type=str, help='SSH 설정 JSON 파일 경로')
    parser.add_argument('--hostname', type=str, help='SSH 서버 호스트명')
    parser.add_argument('--port', type=int, default=22, help='SSH 서버 포트')
    parser.add_argument('--username', type=str, help='SSH 사용자 이름')
    parser.add_argument('--password', type=str, help='SSH 비밀번호')
    parser.add_argument('--key-file', type=str, help='SSH 키 파일 경로')
    parser.add_argument('--base-path', type=str, default='/', help='기본 작업 디렉토리')
    
    args = parser.parse_args()
    
    # 설정 파일에서 SSH 정보 로드
    if args.config:
        with open(args.config, 'r') as f:
            ssh_config = json.load(f)
    else:
        # 명령줄 인수에서 SSH 정보 설정
        ssh_config = {
            'hostname': args.hostname,
            'port': args.port,
            'username': args.username,
            'password': args.password,
            'key_filename': args.key_file,
            'base_path': args.base_path
        }
    
    # 필수 정보 확인
    if not ssh_config.get('hostname'):
        raise ValueError("SSH 호스트명이 필요합니다. --hostname 또는 --config 옵션을 사용하세요.")
    
    if not ssh_config.get('username'):
        raise ValueError("SSH 사용자 이름이 필요합니다. --username 옵션을 사용하세요.")
    
    if not ssh_config.get('password') and not ssh_config.get('key_filename'):
        raise ValueError("SSH 비밀번호 또는 키 파일이 필요합니다. --password 또는 --key-file 옵션을 사용하세요.")
    
    # 서버 설정 및 실행
    server = RemoteSSHFileServer(ssh_config)
    server.setup_handlers()
    
    try:
        print(f"원격 SSH MCP 서버 시작: {ssh_config['hostname']}:{ssh_config.get('port', 22)}")
        await server.server.run_stdio()
    finally:
        # 연결 종료
        await server.fs.remote_close()

if __name__ == "__main__":
    asyncio.run(main())