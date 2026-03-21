"""
Temporary memory system for active poem learning sessions.
Stores full poems in memory with auto-expiry after inactivity.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from threading import Lock


@dataclass
class ActivePoemSession:
    """Represents an active learning session for a poem."""
    user_id: int
    poem_id: int
    poem_title: str
    poem_author: str
    full_text: str
    chunks: List[str] = field(default_factory=list)
    current_chunk_index: int = 0
    last_accessed: float = field(default_factory=time.time)
    learned_chunks: List[int] = field(default_factory=list)  # Indices of chunks user has seen
    
    def touch(self) -> None:
        """Update last accessed time."""
        self.last_accessed = time.time()
    
    def is_expired(self, timeout_seconds: float = 300) -> bool:  # 5 minutes default
        """Check if session has expired due to inactivity."""
        return (time.time() - self.last_accessed) > timeout_seconds
    
    def get_next_chunk(self) -> Optional[str]:
        """Get the next chunk of the poem for learning."""
        if self.current_chunk_index < len(self.chunks):
            chunk = self.chunks[self.current_chunk_index]
            if self.current_chunk_index not in self.learned_chunks:
                self.learned_chunks.append(self.current_chunk_index)
            self.current_chunk_index += 1
            self.touch()
            return chunk
        return None
    
    def get_current_chunk(self) -> Optional[str]:
        """Get the chunk currently being studied (the last one shown to user).
        
        After get_next_chunk() advances the index, the 'current' chunk
        being studied is chunks[index - 1]. At index=0 (initial state,
        before any get_next_chunk call), we return chunks[0].
        """
        if self.current_chunk_index > 0 and self.current_chunk_index <= len(self.chunks):
            return self.chunks[self.current_chunk_index - 1]
        if self.current_chunk_index == 0 and len(self.chunks) > 0:
            return self.chunks[0]
        return None
    
    def peek_chunk(self, index: int) -> Optional[str]:
        """Get chunk by index without advancing pointer."""
        if 0 <= index < len(self.chunks):
            return self.chunks[index]
        return None
    
    def mark_current_chunk_learned(self) -> None:
        """Mark the current chunk as learned without advancing."""
        idx = self.current_chunk_index - 1  # We already advanced in get_next_chunk
        if idx >= 0 and idx not in self.learned_chunks:
            self.learned_chunks.append(idx)
        self.touch()
    
    def get_progress(self) -> dict:
        """Get user's learning progress for this poem."""
        total_chunks = len(self.chunks)
        learned = len(self.learned_chunks)
        
        # Get the last learned text for context
        last_learned_text = ""
        if self.learned_chunks:
            last_chunk_idx = self.learned_chunks[-1]
            last_learned_text = self.chunks[last_chunk_idx][:100] + "..."
        
        return {
            "poem_id": self.poem_id,
            "title": self.poem_title,
            "author": self.poem_author,
            "total_chunks": total_chunks,
            "learned_chunks": learned,
            "progress_percent": round((learned / total_chunks * 100), 1) if total_chunks > 0 else 0,
            "is_complete": self.current_chunk_index >= total_chunks,
            "last_learned_text": last_learned_text,
            "current_chunk_index": self.current_chunk_index
        }


class TemporaryMemory:
    """
    Thread-safe temporary memory store for active poem learning sessions.
    Automatically expires sessions after period of inactivity.
    """
    
    def __init__(self, expiry_seconds: float = 300):  # 5 minutes
        self._sessions: Dict[int, ActivePoemSession] = {}  # user_id -> session
        self._lock = Lock()
        self._expiry_seconds = expiry_seconds
    
    def create_session(
        self,
        user_id: int,
        poem_id: int,
        poem_title: str,
        poem_author: str,
        full_text: str,
        chunk_size: int = 4  # lines per chunk
    ) -> ActivePoemSession:
        """
        Create a new learning session for a poem.
        Splits poem into chunks for gradual learning.
        """
        # Split poem into chunks (by lines or sentences)
        lines = full_text.split('\n')
        chunks = []
        
        for i in range(0, len(lines), chunk_size):
            chunk_lines = lines[i:i + chunk_size]
            chunk_text = '\n'.join(chunk_lines).strip()
            if chunk_text:
                chunks.append(chunk_text)
        
        # If no chunks from line splitting, try sentence splitting
        if not chunks:
            import re
            sentences = re.split(r'[.!?]+', full_text)
            for i in range(0, len(sentences), chunk_size):
                chunk_sentences = sentences[i:i + chunk_size]
                chunk_text = '. '.join(s for s in chunk_sentences if s.strip())
                if chunk_text:
                    chunks.append(chunk_text)
        
        session = ActivePoemSession(
            user_id=user_id,
            poem_id=poem_id,
            poem_title=poem_title,
            poem_author=poem_author,
            full_text=full_text,
            chunks=chunks
        )
        
        with self._lock:
            self._sessions[user_id] = session
        
        return session
    
    def get_session(self, user_id: int) -> Optional[ActivePoemSession]:
        """Get active session for user if exists and not expired."""
        with self._lock:
            session = self._sessions.get(user_id)
            
            if session is None:
                return None
            
            if session.is_expired(self._expiry_seconds):
                # Session expired - remove it
                del self._sessions[user_id]
                return None
            
            session.touch()
            return session
    
    def remove_session(self, user_id: int) -> Optional[ActivePoemSession]:
        """Remove and return a session (e.g., for persisting to DB)."""
        with self._lock:
            return self._sessions.pop(user_id, None)
    
    def cleanup_expired(self) -> List[ActivePoemSession]:
        """Remove and return all expired sessions for persistence."""
        expired = []
        with self._lock:
            expired_user_ids = [
                uid for uid, session in self._sessions.items()
                if session.is_expired(self._expiry_seconds)
            ]
            for uid in expired_user_ids:
                expired.append(self._sessions.pop(uid))
        return expired
    
    def get_all_sessions(self) -> Dict[int, ActivePoemSession]:
        """Get copy of all active sessions."""
        with self._lock:
            return dict(self._sessions)
    
    def has_active_session(self, user_id: int) -> bool:
        """Check if user has an active (non-expired) session."""
        return self.get_session(user_id) is not None


# Global temporary memory instance
temp_memory = TemporaryMemory(expiry_seconds=300)  # 5 minutes


def get_temp_memory() -> TemporaryMemory:
    """Get the global temporary memory instance."""
    return temp_memory
