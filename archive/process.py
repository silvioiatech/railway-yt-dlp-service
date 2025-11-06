import asyncio
import heapq
import json
import logging
import os
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional, NamedTuple

logger = logging.getLogger(__name__)


class DeletionTask(NamedTuple):
    """Task for scheduled file deletion."""
    timestamp: float
    task_id: str
    file_path: Path
    log_callback: Optional[Callable[[str, str], None]]


class FileDeletionScheduler:
    """Centralized scheduler for file deletions with cancellable tasks."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self._heap = []
        self._cancelled_tasks = set()
        self._condition = threading.Condition()
        self._worker_thread = None
        self._shutdown = False
        
        self._start_worker()
    
    def _start_worker(self):
        """Start the background worker thread."""
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._worker_thread = threading.Thread(
                target=self._worker_loop,
                name="FileDeletionWorker",
                daemon=False  # Non-daemon for production reliability
            )
            self._worker_thread.start()
            logger.info("File deletion scheduler worker started")
    
    def _worker_loop(self):
        """Main worker loop that processes scheduled deletions."""
        logger.info("File deletion worker started")
        
        while not self._shutdown:
            with self._condition:
                # Wait until we have tasks or are shutting down
                while not self._heap and not self._shutdown:
                    self._condition.wait()
                
                if self._shutdown:
                    break
                
                # Get the next task
                current_time = time.time()
                
                # Remove cancelled tasks from the front of the heap
                while self._heap and self._heap[0].task_id in self._cancelled_tasks:
                    cancelled_task = heapq.heappop(self._heap)
                    self._cancelled_tasks.discard(cancelled_task.task_id)
                    logger.debug(f"Removed cancelled deletion task: {cancelled_task.task_id}")
                
                if not self._heap:
                    continue
                
                next_task = self._heap[0]
                
                # If it's time to execute, pop and process
                if next_task.timestamp <= current_time:
                    task = heapq.heappop(self._heap)
                    
                    # Check if task was cancelled
                    if task.task_id in self._cancelled_tasks:
                        self._cancelled_tasks.discard(task.task_id)
                        logger.debug(f"Skipping cancelled deletion task: {task.task_id}")
                        continue
                    
                    # Process the deletion outside the lock
                    self._condition.release()
                    try:
                        self._execute_deletion(task)
                    finally:
                        self._condition.acquire()
                else:
                    # Wait until the next task is ready
                    wait_time = next_task.timestamp - current_time
                    self._condition.wait(timeout=min(wait_time, 60))  # Max wait 1 minute
        
        logger.info("File deletion worker stopped")
    
    def _execute_deletion(self, task: DeletionTask):
        """Execute a file deletion task."""
        try:
            if task.file_path.exists():
                task.file_path.unlink()
                msg = f"Auto-deleted file: {task.file_path}"
                logger.info(msg)
                if task.log_callback:
                    task.log_callback(msg, "INFO")
            else:
                msg = f"File already deleted: {task.file_path}"
                logger.debug(msg)
                if task.log_callback:
                    task.log_callback(msg, "INFO")
        except Exception as e:
            msg = f"Failed to auto-delete file {task.file_path}: {e}"
            logger.error(msg)
            if task.log_callback:
                task.log_callback(msg, "ERROR")
    
    def schedule_deletion(self, file_path: Path, delay_seconds: int = 3600, 
                         log_callback: Optional[Callable[[str, str], None]] = None) -> tuple[str, float]:
        """
        Schedule a file for deletion after delay_seconds.
        
        Returns:
            tuple[str, float]: (task_id, scheduled_timestamp)
        """
        task_id = str(uuid.uuid4())
        scheduled_time = time.time() + delay_seconds
        
        task = DeletionTask(
            timestamp=scheduled_time,
            task_id=task_id,
            file_path=file_path,
            log_callback=log_callback
        )
        
        with self._condition:
            heapq.heappush(self._heap, task)
            self._condition.notify()  # Wake up worker
        
        logger.debug(f"Scheduled deletion of {file_path} at {scheduled_time} (task: {task_id})")
        return task_id, scheduled_time
    
    def cancel_deletion(self, task_id: str) -> bool:
        """
        Cancel a scheduled deletion.
        
        Returns:
            bool: True if task was found and cancelled, False otherwise
        """
        with self._condition:
            # Add to cancelled set - worker will skip these tasks
            if any(task.task_id == task_id for task in self._heap):
                self._cancelled_tasks.add(task_id)
                logger.debug(f"Cancelled deletion task: {task_id}")
                return True
            return False
    
    def shutdown(self):
        """Gracefully shutdown the scheduler."""
        logger.info("Shutting down file deletion scheduler")
        
        with self._condition:
            self._shutdown = True
            self._condition.notify_all()
        
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=10)
            if self._worker_thread.is_alive():
                logger.warning("File deletion worker did not shut down gracefully")
        
        logger.info("File deletion scheduler shut down complete")
    
    def get_pending_count(self) -> int:
        """Get the number of pending deletion tasks."""
        with self._condition:
            return len(self._heap) - len(self._cancelled_tasks)


# Global scheduler instance
_deletion_scheduler = FileDeletionScheduler()


def shutdown_deletion_scheduler():
    """Shutdown the global deletion scheduler."""
    global _deletion_scheduler
    if _deletion_scheduler:
        _deletion_scheduler.shutdown()


def get_deletion_scheduler() -> FileDeletionScheduler:
    """Get the global deletion scheduler instance."""
    return _deletion_scheduler

class RailwayStoragePipeline:
    """Manages yt-dlp downloads to Railway storage with auto-deletion after 1 hour."""
    
    def __init__(
        self,
        request_id: str,
        source_url: str,
        storage_dir: str,
        path_template: str,
        yt_dlp_format: str = "bv*+ba/best",
        timeout_sec: int = 1800,
        progress_timeout_sec: int = 300,
        max_content_length: int = 10 * 1024**3,  # 10GB
        cookies: Optional[str] = None,
        log_callback: Optional[Callable[[str, str], None]] = None
    ):
        self.request_id = request_id
        self.source_url = source_url
        self.storage_dir = Path(storage_dir)
        self.path_template = path_template
        self.yt_dlp_format = yt_dlp_format
        self.timeout_sec = timeout_sec
        self.progress_timeout_sec = progress_timeout_sec
        self.max_content_length = max_content_length
        self.cookies = cookies
        self.log_callback = log_callback or (lambda msg, level: None)
        
        self.yt_dlp_proc: Optional[subprocess.Popen] = None
        self.cancelled = False
        self.metadata: Dict[str, Any] = {}
        self.bytes_transferred = 0
        self.file_path: Optional[Path] = None
        self.deletion_time: Optional[float] = None
        self.deletion_task_id: Optional[str] = None
        
        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    def _build_file_path(self, metadata: Dict[str, Any]) -> Path:
        """Build the local file path from template and metadata."""
        from app import expand_path_template
        relative_path = expand_path_template(self.path_template, metadata)
        full_path = self.storage_dir / relative_path
        
        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        return full_path
    
    def _build_yt_dlp_command(self, output_path: Path) -> list[str]:
        """Build yt-dlp command for direct file download."""
        cmd = [
            'yt-dlp',
            '--no-warnings',
            '--format', self.yt_dlp_format,
            '--output', str(output_path),
            '--no-part',
            '--no-mtime',
            '--no-playlist',
            self.source_url
        ]
        
        if self.cookies:
            cmd.extend(['--cookies', self.cookies])
        
        return cmd
    
    def _schedule_deletion(self, file_path: Path, delay_seconds: int = 3600) -> str:
        """
        Schedule file deletion using the centralized scheduler.
        
        Args:
            file_path: Path to the file to delete
            delay_seconds: Delay in seconds before deletion (default: 1 hour)
            
        Returns:
            str: Cancellable task ID for the scheduled deletion
        """
        task_id, scheduled_time = _deletion_scheduler.schedule_deletion(
            file_path=file_path,
            delay_seconds=delay_seconds,
            log_callback=self.log_callback
        )
        
        # Store deletion info for tracking
        self.deletion_task_id = task_id
        self.deletion_time = scheduled_time
        
        self._log(f"Scheduled deletion of {file_path} in {delay_seconds} seconds (task: {task_id})")
        return task_id
    
    def cancel_deletion(self) -> bool:
        """
        Cancel the scheduled deletion for this pipeline.
        
        Returns:
            bool: True if deletion was cancelled, False if no deletion was scheduled
        """
        if self.deletion_task_id:
            success = _deletion_scheduler.cancel_deletion(self.deletion_task_id)
            if success:
                self._log(f"Cancelled scheduled deletion (task: {self.deletion_task_id})")
                self.deletion_task_id = None
                self.deletion_time = None
            return success
        return False
    
    async def _monitor_progress(self, yt_dlp_proc: subprocess.Popen, file_path: Path):
        """Monitor download progress and handle timeouts."""
        last_progress_time = asyncio.get_event_loop().time()
        last_file_size = 0
        
        # Buffer for reading yt-dlp stderr (for progress info)
        stderr_buffer = b""
        
        while True:
            if self.cancelled:
                break
            
            current_time = asyncio.get_event_loop().time()
            
            # Check if process is still alive
            if yt_dlp_proc.poll() is not None:
                break
            
            # Check file size progress
            if file_path.exists():
                current_size = file_path.stat().st_size
                if current_size > last_file_size:
                    last_progress_time = current_time
                    last_file_size = current_size
                    self.bytes_transferred = current_size
            
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
            
            await asyncio.sleep(1)
    
    async def execute(self) -> Dict[str, Any]:
        """Execute the Railway storage pipeline."""
        
        try:
            # Step 1: Extract metadata
            self.metadata = await self._get_metadata()
            
            # Step 2: Build file path
            self.file_path = self._build_file_path(self.metadata)
            self._log(f"Target file path: {self.file_path}")
            
            # Step 3: Start download
            self._log("Starting download to Railway storage...")
            
            yt_dlp_cmd = self._build_yt_dlp_command(self.file_path)
            self._log(f"yt-dlp command: {' '.join(yt_dlp_cmd[:5])}...")  # Log partial command for security
            
            # Start yt-dlp process
            self.yt_dlp_proc = subprocess.Popen(
                yt_dlp_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )
            
            # Step 4: Monitor progress with timeout
            try:
                await asyncio.wait_for(
                    self._monitor_progress(self.yt_dlp_proc, self.file_path),
                    timeout=self.timeout_sec
                )
            except asyncio.TimeoutError:
                self._log(f"Download timed out after {self.timeout_sec}s", "ERROR")
                raise
            
            # Step 5: Wait for completion and check results
            yt_dlp_returncode = self.yt_dlp_proc.wait()
            
            # Get stderr from process
            _, yt_dlp_stderr = self.yt_dlp_proc.communicate() if self.yt_dlp_proc.stderr else (None, b"")
            
            # Check for errors
            if yt_dlp_returncode != 0:
                error_msg = yt_dlp_stderr.decode('utf-8', errors='ignore')
                raise RuntimeError(f"yt-dlp failed (exit {yt_dlp_returncode}): {error_msg}")
            
            # Verify file exists and get final size
            if not self.file_path.exists():
                raise RuntimeError("Download completed but file not found")
            
            self.bytes_transferred = self.file_path.stat().st_size
            self._log(f"Download completed successfully. File size: {self.bytes_transferred} bytes")
            
            # Step 6: Schedule auto-deletion after 1 hour
            self._schedule_deletion(self.file_path)
            self._log("Scheduled auto-deletion in 1 hour")
            
            return {
                'success': True,
                'file_path': str(self.file_path.relative_to(self.storage_dir)),
                'absolute_path': str(self.file_path),
                'bytes_transferred': self.bytes_transferred,
                'metadata': self.metadata,
                'deletion_time': self.deletion_time
            }
            
        except Exception as e:
            self._log(f"Download failed: {str(e)}", "ERROR")
            # Clean up partial file if it exists
            if self.file_path and self.file_path.exists():
                try:
                    self.file_path.unlink()
                    self._log("Cleaned up partial download file")
                except Exception as cleanup_error:
                    self._log(f"Failed to clean up partial file: {cleanup_error}", "WARNING")
            raise
        
        finally:
            await self._cleanup()
    
    async def _cleanup(self):
        """Clean up processes and cancel scheduled deletion if needed."""
        self.cancelled = True
        
        # Cancel scheduled deletion if pipeline is being cleaned up early
        if self.deletion_task_id:
            self.cancel_deletion()
        
        if self.yt_dlp_proc and self.yt_dlp_proc.poll() is None:
            try:
                self._log("Terminating yt-dlp process...")
                self.yt_dlp_proc.terminate()
                
                # Wait briefly for graceful termination
                try:
                    self.yt_dlp_proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._log("Force killing yt-dlp process...")
                    self.yt_dlp_proc.kill()
                    self.yt_dlp_proc.wait()
                    
            except Exception as e:
                self._log(f"Error cleaning up yt-dlp process: {e}", "WARNING")
    
    def cancel(self):
        """Cancel the pipeline."""
        self.cancelled = True
        asyncio.create_task(self._cleanup())