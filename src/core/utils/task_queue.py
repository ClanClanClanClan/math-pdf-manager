#!/usr/bin/env python3
"""
Basic task queue system for paper downloads and processing.
"""

import json
import time
import logging
import threading
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from queue import Queue, Empty
import uuid

logger = logging.getLogger("task_queue")

class TaskType(Enum):
    DOWNLOAD_PAPER = "download_paper"
    FETCH_METADATA = "fetch_metadata" 
    ORGANIZE_PAPER = "organize_paper"
    UPDATE_ARXIV = "update_arxiv"
    VALIDATE_COLLECTION = "validate_collection"

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3

@dataclass
class Task:
    id: str
    task_type: TaskType
    priority: Priority
    status: TaskStatus
    created_at: datetime
    scheduled_for: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    attempts: int = 0
    max_attempts: int = 3
    data: Dict[str, Any] = None
    result: Dict[str, Any] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.result is None:
            self.result = {}

class TaskQueue:
    """Simple in-memory task queue with persistence."""
    
    def __init__(self, persist_file: Optional[Path] = None):
        self.tasks: Dict[str, Task] = {}
        self.queue = Queue()
        self.persist_file = persist_file
        self.workers: List[threading.Thread] = []
        self.running = False
        self.task_handlers: Dict[TaskType, Callable] = {}
        
        # Load persisted tasks
        if self.persist_file and self.persist_file.exists():
            self._load_tasks()
    
    def add_task(self, task_type: TaskType, data: Dict[str, Any], 
                 priority: Priority = Priority.MEDIUM,
                 scheduled_for: Optional[datetime] = None) -> str:
        """Add a new task to the queue."""
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            task_type=task_type,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            scheduled_for=scheduled_for,
            data=data
        )
        
        self.tasks[task_id] = task
        
        # Add to queue if not scheduled for future
        if not scheduled_for or scheduled_for <= datetime.now():
            self.queue.put((priority.value, task_id))
            logger.info(f"Added task {task_id} ({task_type.value}) to queue")
        else:
            logger.info(f"Scheduled task {task_id} ({task_type.value}) for {scheduled_for}")
        
        self._persist_tasks()
        return task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[Task]:
        """Get all tasks with given status."""
        return [task for task in self.tasks.values() if task.status == status]
    
    def get_tasks_by_type(self, task_type: TaskType) -> List[Task]:
        """Get all tasks of given type."""
        return [task for task in self.tasks.values() if task.task_type == task_type]
    
    def register_handler(self, task_type: TaskType, handler: Callable):
        """Register a handler function for a task type."""
        self.task_handlers[task_type] = handler
        logger.info(f"Registered handler for {task_type.value}")
    
    def start_workers(self, num_workers: int = 2):
        """Start worker threads to process tasks."""
        if self.running:
            logger.warning("Workers already running")
            return
        
        self.running = True
        logger.info(f"Starting {num_workers} worker threads")
        
        for i in range(num_workers):
            worker = threading.Thread(target=self._worker_loop, args=(i,))
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
    
    def stop_workers(self):
        """Stop all worker threads."""
        self.running = False
        logger.info("Stopping worker threads")
        
        # Add sentinel values to wake up workers
        for _ in self.workers:
            self.queue.put((999, None))
        
        # Wait for workers to finish
        for worker in self.workers:
            worker.join(timeout=5)
        
        self.workers.clear()
    
    def _worker_loop(self, worker_id: int):
        """Main worker loop."""
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Get next task (with timeout to check running status)
                priority, task_id = self.queue.get(timeout=1)
                
                if task_id is None:  # Sentinel value
                    break
                
                task = self.tasks.get(task_id)
                if not task:
                    continue
                
                # Check if task is ready to run
                if task.scheduled_for and task.scheduled_for > datetime.now():
                    # Re-queue for later
                    self.queue.put((priority, task_id))
                    time.sleep(1)
                    continue
                
                # Process the task
                self._process_task(task, worker_id)
                
            except Empty:
                continue  # Timeout, check if still running
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
        
        logger.info(f"Worker {worker_id} stopped")
    
    def _process_task(self, task: Task, worker_id: int):
        """Process a single task."""
        logger.info(f"Worker {worker_id} processing task {task.id} ({task.task_type.value})")
        
        # Update task status
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        task.attempts += 1
        self._persist_tasks()
        
        try:
            # Get handler for task type
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise Exception(f"No handler registered for {task.task_type.value}")
            
            # Execute handler
            result = handler(task.data)
            
            # Task completed successfully
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result if isinstance(result, dict) else {"result": result}
            logger.info(f"Task {task.id} completed successfully")
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            task.error_message = str(e)
            
            # Check if we should retry
            if task.attempts < task.max_attempts:
                task.status = TaskStatus.PENDING
                # Re-queue with delay
                delay_seconds = 2 ** task.attempts  # Exponential backoff
                task.scheduled_for = datetime.now() + timedelta(seconds=delay_seconds)
                self.queue.put((task.priority.value, task.id))
                logger.info(f"Task {task.id} will retry in {delay_seconds}s (attempt {task.attempts}/{task.max_attempts})")
            else:
                task.status = TaskStatus.FAILED
                logger.error(f"Task {task.id} failed after {task.max_attempts} attempts")
        
        self._persist_tasks()
    
    def _persist_tasks(self):
        """Save tasks to disk."""
        if not self.persist_file:
            return
        
        try:
            # Convert tasks to serializable format
            task_data = {}
            for task_id, task in self.tasks.items():
                task_dict = asdict(task)
                # Convert datetime objects to ISO strings
                for field in ['created_at', 'scheduled_for', 'started_at', 'completed_at']:
                    if task_dict[field]:
                        task_dict[field] = task_dict[field].isoformat()
                # Convert enums to values
                task_dict['task_type'] = task.task_type.value
                task_dict['status'] = task.status.value
                task_dict['priority'] = task.priority.value
                task_data[task_id] = task_dict
            
            # Write to file
            with open(self.persist_file, 'w') as f:
                json.dump(task_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to persist tasks: {e}")
    
    def _load_tasks(self):
        """Load tasks from disk."""
        try:
            with open(self.persist_file, 'r') as f:
                task_data = json.load(f)
            
            for task_id, task_dict in task_data.items():
                # Convert ISO strings back to datetime objects
                for field in ['created_at', 'scheduled_for', 'started_at', 'completed_at']:
                    if task_dict[field]:
                        task_dict[field] = datetime.fromisoformat(task_dict[field])
                
                # Convert values back to enums
                task_dict['task_type'] = TaskType(task_dict['task_type'])
                task_dict['status'] = TaskStatus(task_dict['status'])
                task_dict['priority'] = Priority(task_dict['priority'])
                
                task = Task(**task_dict)
                self.tasks[task_id] = task
                
                # Re-queue pending tasks
                if task.status == TaskStatus.PENDING:
                    if not task.scheduled_for or task.scheduled_for <= datetime.now():
                        self.queue.put((task.priority.value, task_id))
            
            logger.info(f"Loaded {len(self.tasks)} tasks from {self.persist_file}")
            
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        stats = {
            "total_tasks": len(self.tasks),
            "by_status": {},
            "by_type": {},
            "queue_size": self.queue.qsize(),
            "workers_running": len(self.workers),
            "system_running": self.running
        }
        
        for status in TaskStatus:
            stats["by_status"][status.value] = len(self.get_tasks_by_status(status))
        
        for task_type in TaskType:
            stats["by_type"][task_type.value] = len(self.get_tasks_by_type(task_type))
        
        return stats


# Global task queue instance
_task_queue: Optional[TaskQueue] = None

def get_task_queue() -> TaskQueue:
    """Get or create the global task queue."""
    global _task_queue
    if _task_queue is None:
        persist_file = Path.home() / ".academic_papers" / "task_queue.json"
        persist_file.parent.mkdir(exist_ok=True)
        _task_queue = TaskQueue(persist_file)
    return _task_queue