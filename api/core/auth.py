"""
API Key management.

Multi-tenant API key system with rate limiting and quotas.
"""

import hashlib
import secrets
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import redis

from api.config import api_config
from api.models import (
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyWithSecret,
    UsageStats,
)


def hash_key(key: str) -> str:
    """Hash an API key for storage."""
    return hashlib.sha256(key.encode()).hexdigest()


def generate_key(prefix: str) -> str:
    """Generate a new API key."""
    random_part = secrets.token_urlsafe(24)[:32]
    return f"{prefix}{random_part}"


class ApiKeyStore:
    """SQLite-backed API key store."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the store."""
        if db_path is None:
            base_path = api_config.storage.base_path.parent
            base_path.mkdir(parents=True, exist_ok=True)
            db_path = base_path / "data" / "api_keys.db"
        else:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY,
                    key_hash TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    owner_email TEXT,
                    is_active INTEGER DEFAULT 1,
                    rate_limit_rpm INTEGER DEFAULT 60,
                    rate_limit_rph INTEGER DEFAULT 1000,
                    concurrent_tasks INTEGER DEFAULT 3,
                    total_tasks_limit INTEGER,
                    tasks_used INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    expires_at TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_api_keys_key_hash
                ON api_keys(key_hash)
            """)
            conn.commit()

    @contextmanager
    def _get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def create_key(self, request: ApiKeyCreateRequest) -> ApiKeyWithSecret:
        """Create a new API key."""
        key_id = uuid4()
        key = generate_key(api_config.apikey.key_prefix)
        key_hash_val = hash_key(key)
        
        now = datetime.utcnow()
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO api_keys (
                    id, key_hash, project_name, owner_email,
                    is_active, rate_limit_rpm, rate_limit_rph,
                    concurrent_tasks, total_tasks_limit, tasks_used,
                    created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(key_id),
                key_hash_val,
                request.project_name,
                request.owner_email,
                1,
                request.rate_limit_rpm,
                request.rate_limit_rph,
                request.concurrent_tasks,
                request.total_tasks_limit,
                0,
                now.isoformat(),
                request.expires_at.isoformat() if request.expires_at else None,
            ))
            conn.commit()
        
        return ApiKeyWithSecret(
            id=key_id,
            key=key,
            project_name=request.project_name,
            expires_at=request.expires_at,
        )

    def get_key(self, key_id: UUID) -> Optional[ApiKeyResponse]:
        """Get API key by ID."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM api_keys WHERE id = ?",
                (str(key_id),)
            )
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_response(row)

    def validate_key(self, key: str) -> Optional[ApiKeyResponse]:
        """Validate an API key and return the key info."""
        key_hash_val = hash_key(key)
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM api_keys WHERE key_hash = ? AND is_active = 1",
                (key_hash_val,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            
            # Check expiration
            if row["expires_at"]:
                expires = datetime.fromisoformat(row["expires_at"])
                if expires < datetime.utcnow():
                    return None
            
            return self._row_to_response(row)

    def list_keys(self) -> List[ApiKeyResponse]:
        """List all API keys."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM api_keys ORDER BY created_at DESC")
            return [self._row_to_response(row) for row in cursor.fetchall()]

    def revoke_key(self, key_id: UUID) -> bool:
        """Revoke an API key."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE api_keys SET is_active = 0 WHERE id = ?",
                (str(key_id),)
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_key(self, key_id: UUID) -> bool:
        """Delete an API key."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM api_keys WHERE id = ?",
                (str(key_id),)
            )
            conn.commit()
            return cursor.rowcount > 0

    def increment_usage(self, key_id: UUID) -> bool:
        """Increment task usage count."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE api_keys SET tasks_used = tasks_used + 1 WHERE id = ?",
                (str(key_id),)
            )
            conn.commit()
            return cursor.rowcount > 0

    def get_usage_stats(self) -> UsageStats:
        """Get usage statistics."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_keys,
                    SUM(is_active) as active_keys,
                    SUM(tasks_used) as total_tasks
                FROM api_keys
            """)
            row = cursor.fetchone()
            
            return UsageStats(
                total_requests=0,  # Would need request logging
                total_tasks=row["total_tasks"] or 0,
                active_keys=row["active_keys"] or 0,
            )

    def _row_to_response(self, row: sqlite3.Row) -> ApiKeyResponse:
        """Convert row to response."""
        return ApiKeyResponse(
            id=UUID(row["id"]),
            key_prefix=row["key_hash"][:8],
            project_name=row["project_name"],
            owner_email=row["owner_email"],
            is_active=bool(row["is_active"]),
            rate_limit_rpm=row["rate_limit_rpm"],
            rate_limit_rph=row["rate_limit_rph"],
            concurrent_tasks=row["concurrent_tasks"],
            total_tasks_limit=row["total_tasks_limit"],
            tasks_used=row["tasks_used"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=datetime.fromisoformat(row["expires_at"]) if row["expires_at"] else None,
        )


class RateLimiter:
    """Redis-backed rate limiter."""

    def __init__(self):
        """Initialize rate limiter."""
        self._redis: Optional[redis.Redis] = None
        self.window = api_config.rate_limit.window_seconds

    def _get_redis(self) -> redis.Redis:
        """Get Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(api_config.redis.url)
        return self._redis

    def check_rate_limit(
        self,
        key_id: UUID,
        rpm: int,
        rph: int,
    ) -> tuple[bool, str]:
        """Check rate limit. Returns (allowed, reason)."""
        redis_client = self._get_redis()
        
        # Check minute limit
        minute_key = f"rate:{key_id}:minute"
        minute_count = redis_client.get(minute_key)
        
        if minute_count and int(minute_count) >= rpm:
            return False, "Rate limit exceeded (requests per minute)"
        
        # Check hour limit
        hour_key = f"rate:{key_id}:hour"
        hour_count = redis_client.get(hour_key)
        
        if hour_count and int(hour_count) >= rph:
            return False, "Rate limit exceeded (requests per hour)"
        
        # Increment counters
        pipe = redis_client.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 60)
        pipe.incr(hour_key)
        pipe.expire(hour_key, 3600)
        pipe.execute()
        
        return True, ""

    def get_remaining(
        self,
        key_id: UUID,
        rpm: int,
        rph: int,
    ) -> Dict[str, int]:
        """Get remaining requests."""
        redis_client = self._get_redis()
        
        minute_key = f"rate:{key_id}:minute"
        hour_key = f"rate:{key_id}:hour"
        
        minute_count = int(redis_client.get(minute_key) or 0)
        hour_count = int(redis_client.get(hour_key) or 0)
        
        return {
            "remaining_rpm": max(0, rpm - minute_count),
            "remaining_rph": max(0, rph - hour_count),
        }

    def reset(self, key_id: UUID):
        """Reset rate limits for a key."""
        redis_client = self._get_redis()
        redis_client.delete(f"rate:{key_id}:minute", f"rate:{key_id}:hour")


# Global instances
api_key_store = ApiKeyStore()
rate_limiter = RateLimiter()