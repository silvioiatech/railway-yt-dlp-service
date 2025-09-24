import asyncio
import json
import logging
import os
import re
import signal
import subprocess
from typing import Any, Callable, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

class StreamingPipeline:
    """Manages yt-dlp to rclone streaming pipeline with no temporary files."""
    
    def __init__(
        self,
        request_id: str,
        source_url: str,
        rclone_remote: str,
        path_template: str,
        yt_dlp_format: str = "bv*+ba/best",
        timeout_sec: int = 1800,
        progress_timeout_sec: int = 300,
        max_content_length: int = 10 * 1024**3,  # 10GB
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[str] = None,
        content_type: Optional[str] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.request_id = request_id
        self.source_url = source_url
        self.rclone_remote = rclone_remote
        self.path_template = path_template
        self.yt_dlp_format = yt_dlp_format
        self.timeout_sec = timeout_sec
        self.progress_timeout_sec = progress_timeout_sec
        self.max_content_length = max_content_length
        self.headers = headers or {}
        self.cookies = cookies
        self.content_type = content_type
        self.log_callback = log_callback or (lambda msg, level: None)
        
        self.yt_dlp_proc: Optional[subprocess.Popen] = None
        self.rclone_proc: Optional[subprocess.Popen] = None
        self.cancelled = False
        self.metadata: Dict[str, Any] = {}
        self.bytes_transferred = 0
        self.object_path: Optional[str] = None
    
    def _log(self, message: str, level: str = "INFO"):
        """Log with callback."""
        logger.log(getattr(logging, level), f"[{self.request_id}] {message}")
        self.log_callback(message, level)
    
    async def _get_metadata(self) -> Dict[str, Any]:
        """Extract metadata from source URL using yt-dlp."""
        self._log("Extracting metadata...")
        
        cmd = [
            'yt-dlp',
            '--dump-json',
            '--no-warnings',
            '--format', self.yt_dlp_format,
            self.source_url
        ]
        
        if self.cookies:
            cmd.extend(['--cookies', self.cookies])
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), 
                timeout=60  # Metadata extraction should be quick
            )
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                raise RuntimeError(f"Metadata extraction failed: {error_msg}")
            
            # Parse JSON output
            json_lines = stdout.decode('utf-8').strip().split('\n')
            for line in json_lines:
                if line.strip():
                    try:
                        metadata = json.loads(line)
                        if metadata.get('_type') != 'playlist':  # Skip playlist entries
                            self._log(f"Extracted metadata for: {metadata.get('title', 'Unknown')}")
                            return metadata
                    except json.JSONDecodeError:
                        continue
            
            raise RuntimeError("No valid metadata found in yt-dlp output")
            
        except asyncio.TimeoutError:
            raise RuntimeError("Metadata extraction timed out")
        except Exception as e:
            raise RuntimeError(f"Metadata extraction failed: {str(e)}")
    
    def _build_object_path(self, metadata: Dict[str, Any]) -> str:
        """Build the object storage path from template and metadata."""
        from app import expand_path_template
        return expand_path_template(self.path_template, metadata)
    
    def _build_yt_dlp_command(self) -> list[str]:
        """Build yt-dlp command for streaming."""
        cmd = [
            'yt-dlp',
            '--no-warnings',
            '--format', self.yt_dlp_format,
            '--output', '-',  # Stream to stdout
            '--no-part',
            '--no-mtime',
            '--no-playlist',
            self.source_url
        ]
        
        if self.cookies:
            cmd.extend(['--cookies', self.cookies])
        
        return cmd
    
    def _build_rclone_command(self, object_path: str) -> list[str]:
        """Build rclone command for uploading."""
        cmd = [
            'rclone',
            'rcat',
            f"{self.rclone_remote}:{object_path}",
            '--buffer-size', '8M',
            '--transfers', '1',
            '--retries', '5',
            '--low-level-retries', '10',
            '--multi-thread-streams', '0',
            '--progress=false',
            '--stats=0'
        ]
        
        # Add custom headers
        headers_to_add = {}
        
        # Set content-type
        if self.content_type:
            headers_to_add['Content-Type'] = self.content_type
        elif not any(h.lower() == 'content-type' for h in self.headers):
            # Default to video/mp4 if not specified
            headers_to_add['Content-Type'] = 'video/mp4'
        
        # Add user-specified headers
        headers_to_add.update(self.headers)
        
        # Apply headers to rclone command
        for key, value in headers_to_add.items():
            cmd.extend(['--header', f"{key}: {value}"])
        
        return cmd
    
    async def _monitor_progress(self, yt_dlp_proc: subprocess.Popen, rclone_proc: subprocess.Popen):
        """Monitor pipeline progress and handle timeouts."""
        last_progress_time = asyncio.get_event_loop().time()
        bytes_read = 0
        
        # Buffer for reading yt-dlp stderr (for progress info)
        stderr_buffer = b""
        
        while True:
            if self.cancelled:
                break
            
            current_time = asyncio.get_event_loop().time()
            
            # Check if processes are still alive
            if yt_dlp_proc.poll() is not None and rclone_proc.poll() is not None:
                break
            
            # Check for progress timeout
            if current_time - last_progress_time > self.progress_timeout_sec:
                self._log(f"No progress for {self.progress_timeout_sec}s, aborting", "WARNING")
                raise asyncio.TimeoutError("Progress timeout")
            
            # Read stderr from yt-dlp for progress updates
            if yt_dlp_proc.stderr:
                try:
                    # Non-blocking read
                    chunk = yt_dlp_proc.stderr.read(1024)
                    if chunk:
                        stderr_buffer += chunk
                        last_progress_time = current_time
                        
                        # Process complete lines
                        while b'\n' in stderr_buffer:
                            line, stderr_buffer = stderr_buffer.split(b'\n', 1)
                            line_str = line.decode('utf-8', errors='ignore').strip()
                            
                            # Look for progress indicators
                            if any(indicator in line_str.lower() for indicator in ['%', 'downloading', 'progress']):
                                self._log(f"Progress: {line_str}")
                
                except (BlockingIOError, OSError):
                    pass  # No data available
            
            # Estimate bytes transferred (rough approximation)
            # In a real implementation, you might want to monitor the pipe more closely
            if hasattr(rclone_proc, 'stdin') and rclone_proc.stdin:
                # This is a simplified progress tracking
                # You could implement more sophisticated monitoring
                pass
            
            await asyncio.sleep(1)
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the streaming pipeline."""
        
        try:
            # Step 1: Extract metadata
            self.metadata = await self._get_metadata()
            
            # Step 2: Build object path
            self.object_path = self._build_object_path(self.metadata)
            self._log(f"Target object path: {self.object_path}")
            
            # Step 3: Start processes
            self._log("Starting streaming pipeline...")
            
            yt_dlp_cmd = self._build_yt_dlp_command()
            rclone_cmd = self._build_rclone_command(self.object_path)
            
            self._log(f"yt-dlp command: {' '.join(yt_dlp_cmd[:5])}...")  # Log partial command for security
            self._log(f"rclone command: {' '.join(rclone_cmd[:5])}...")
            
            # Start yt-dlp process
            self.yt_dlp_proc = subprocess.Popen(
                yt_dlp_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # Start rclone process
            self.rclone_proc = subprocess.Popen(
                rclone_cmd,
                stdin=self.yt_dlp_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # Close yt-dlp stdout in parent to allow EOF propagation
            if self.yt_dlp_proc.stdout:
                self.yt_dlp_proc.stdout.close()
            
            # Step 4: Monitor progress with timeout
            try:
                await asyncio.wait_for(
                    self._monitor_progress(self.yt_dlp_proc, self.rclone_proc),
                    timeout=self.timeout_sec
                )
            except asyncio.TimeoutError:
                self._log(f"Pipeline timed out after {self.timeout_sec}s", "ERROR")
                raise
            
            # Step 5: Wait for completion and check results
            yt_dlp_returncode = self.yt_dlp_proc.wait()
            rclone_returncode = self.rclone_proc.wait()
            
            # Get stderr from both processes
            _, yt_dlp_stderr = self.yt_dlp_proc.communicate() if self.yt_dlp_proc.stderr else (None, b"")
            _, rclone_stderr = self.rclone_proc.communicate() if self.rclone_proc.stderr else (None, b"")
            
            # Check for errors
            if yt_dlp_returncode != 0:
                error_msg = yt_dlp_stderr.decode('utf-8', errors='ignore')
                raise RuntimeError(f"yt-dlp failed (exit {yt_dlp_returncode}): {error_msg}")
            
            if rclone_returncode != 0:
                error_msg = rclone_stderr.decode('utf-8', errors='ignore')
                raise RuntimeError(f"rclone failed (exit {rclone_returncode}): {error_msg}")
            
            self._log("Pipeline completed successfully")
            
            # Extract bytes transferred from rclone output if available
            rclone_output = rclone_stderr.decode('utf-8', errors='ignore')
            bytes_match = re.search(r'Transferred:\s+[\d.]+\s*[KMGT]?B\s*\((\d+)\s*bytes?\)', rclone_output)
            if bytes_match:
                self.bytes_transferred = int(bytes_match.group(1))
            
            return {
                'success': True,
                'object_path': self.object_path,
                'bytes_transferred': self.bytes_transferred,
                'metadata': self.metadata
            }
            
        except Exception as e:
            self._log(f"Pipeline failed: {str(e)}", "ERROR")
            raise
        
        finally:
            await self._cleanup()
    
    async def _cleanup(self):
        """Clean up processes."""
        self.cancelled = True
        
        for proc, name in [(self.rclone_proc, 'rclone'), (self.yt_dlp_proc, 'yt-dlp')]:
            if proc and proc.poll() is None:
                try:
                    self._log(f"Terminating {name} process...")
                    proc.terminate()
                    
                    # Wait briefly for graceful termination
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._log(f"Force killing {name} process...")
                        proc.kill()
                        proc.wait()
                        
                except Exception as e:
                    self._log(f"Error cleaning up {name} process: {e}", "WARNING")
    
    def cancel(self):
        """Cancel the pipeline."""
        self.cancelled = True
        asyncio.create_task(self._cleanup())