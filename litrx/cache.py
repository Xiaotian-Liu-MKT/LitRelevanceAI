"""
Result caching system for LitRx Toolkit.
Caches AI analysis results to avoid redundant API calls and improve performance.
"""
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

from .logging_config import get_logger

logger = get_logger(__name__)


class ResultCache:
    """Cache system for AI analysis results."""

    def __init__(self, cache_dir: Optional[Path] = None, ttl_days: int = 30):
        """
        Initialize the cache system.

        Args:
            cache_dir: Directory for cache files (defaults to ~/.litrx/cache)
            ttl_days: Time-to-live in days for cached results (default: 30)
        """
        if cache_dir is None:
            cache_dir = Path.home() / ".litrx" / "cache"

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(days=ttl_days)

        logger.info(f"ResultCache initialized: {self.cache_dir}, TTL={ttl_days} days")

    def _get_cache_key(self, title: str, abstract: str, questions: str = "") -> str:
        """
        Generate a cache key from content.

        Args:
            title: Paper title
            abstract: Paper abstract
            questions: Questions/prompts (optional, for differentiation)

        Returns:
            SHA256 hash as hex string
        """
        content = f"{title}|{abstract}|{questions}"
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _get_cache_path(self, cache_key: str) -> Path:
        """Get the file path for a cache key."""
        # Use subdirectories to avoid too many files in one directory
        subdir = cache_key[:2]
        cache_subdir = self.cache_dir / subdir
        cache_subdir.mkdir(exist_ok=True)
        return cache_subdir / f"{cache_key}.json"

    def get(self, title: str, abstract: str, questions: str = "") -> Optional[Dict[str, Any]]:
        """
        Retrieve cached result.

        Args:
            title: Paper title
            abstract: Paper abstract
            questions: Questions/prompts

        Returns:
            Cached result dict or None if not found/expired
        """
        cache_key = self._get_cache_key(title, abstract, questions)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            logger.debug(f"Cache miss: {cache_key[:8]}...")
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)

            # Check expiration
            cached_time = datetime.fromisoformat(cached_data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                logger.debug(f"Cache expired: {cache_key[:8]}...")
                cache_path.unlink()  # Delete expired cache
                return None

            logger.debug(f"Cache hit: {cache_key[:8]}...")
            return cached_data['result']

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Log detailed error information
            logger.warning(
                f"Invalid cache file detected - "
                f"Key: {cache_key}, Path: {cache_path}, "
                f"Error type: {type(e).__name__}, Message: {e}"
            )

            # Create backup before deletion
            backup_path = cache_path.with_suffix('.json.corrupt')
            try:
                import shutil
                shutil.copy2(cache_path, backup_path)
                logger.info(f"Corrupted cache backed up to: {backup_path}")
            except Exception as backup_error:
                logger.error(f"Failed to backup corrupted cache: {backup_error}")

            # Delete corrupted cache
            try:
                cache_path.unlink()
                logger.info(f"Corrupted cache deleted: {cache_path}")
            except Exception as delete_error:
                logger.error(f"Failed to delete corrupted cache: {delete_error}")

            return None

    def set(self, title: str, abstract: str, result: Dict[str, Any], questions: str = "") -> None:
        """
        Store result in cache.

        Args:
            title: Paper title
            abstract: Paper abstract
            result: Analysis result to cache
            questions: Questions/prompts
        """
        cache_key = self._get_cache_key(title, abstract, questions)
        cache_path = self._get_cache_path(cache_key)

        cached_data = {
            'timestamp': datetime.now().isoformat(),
            'title': title[:100],  # Store truncated title for debugging
            'result': result
        }

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cached_data, f, ensure_ascii=False, indent=2)
            logger.debug(f"Cached result: {cache_key[:8]}...")
        except Exception as e:
            logger.error(f"Failed to cache result: {e}")

    def clear_expired(self) -> int:
        """
        Remove expired cache entries.

        Returns:
            Number of entries removed
        """
        logger.info("Clearing expired cache entries...")
        removed_count = 0

        try:
            for cache_file in self.cache_dir.rglob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)

                    cached_time = datetime.fromisoformat(cached_data['timestamp'])
                    if datetime.now() - cached_time > self.ttl:
                        cache_file.unlink()
                        removed_count += 1
                        logger.debug(f"Removed expired cache: {cache_file.name}")
                except Exception as e:
                    # Log and backup corrupted files before deletion
                    logger.warning(f"Corrupted cache file during cleanup: {cache_file}, Error: {e}")
                    try:
                        backup_path = cache_file.with_suffix('.json.corrupt')
                        import shutil
                        shutil.copy2(cache_file, backup_path)
                        logger.info(f"Backed up corrupted cache to: {backup_path}")
                    except Exception as backup_error:
                        logger.error(f"Failed to backup during cleanup: {backup_error}")

                    # Delete corrupted files
                    try:
                        cache_file.unlink()
                        removed_count += 1
                        logger.debug(f"Removed corrupted cache: {cache_file.name}")
                    except Exception as delete_error:
                        logger.error(f"Failed to delete corrupted cache: {delete_error}")

        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

        logger.info(f"Cleared {removed_count} expired/corrupted cache entries")
        return removed_count

    def clear_all(self) -> int:
        """
        Remove all cache entries.

        Returns:
            Number of entries removed
        """
        logger.info("Clearing all cache entries...")
        removed_count = 0

        try:
            for cache_file in self.cache_dir.rglob("*.json"):
                cache_file.unlink()
                removed_count += 1
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")

        logger.info(f"Cleared {removed_count} cache entries")
        return removed_count

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        total_files = 0
        total_size = 0
        expired_count = 0

        try:
            for cache_file in self.cache_dir.rglob("*.json"):
                total_files += 1
                total_size += cache_file.stat().st_size

                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    cached_time = datetime.fromisoformat(cached_data['timestamp'])
                    if datetime.now() - cached_time > self.ttl:
                        expired_count += 1
                except Exception:
                    expired_count += 1

        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")

        return {
            'total_entries': total_files,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'expired_entries': expired_count,
            'cache_dir': str(self.cache_dir)
        }


# Global cache instance
_cache_instance: Optional[ResultCache] = None


def get_cache() -> ResultCache:
    """Get or create the global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = ResultCache()
    return _cache_instance
