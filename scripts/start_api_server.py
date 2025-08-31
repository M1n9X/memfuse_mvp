#!/usr/bin/env python3
"""
Script to start the MemFuse API server.
Handles database migration and service initialization.
"""

import os
import sys
import subprocess
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from memfuse.config import Settings
from memfuse.db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_database_migrations():
    """Run database migrations to set up API schema."""
    try:
        settings = Settings.from_env()
        db = Database.from_settings(settings)
        
        # Get all SQL files in order
        init_dir = project_root / "db" / "init"
        sql_files = sorted(init_dir.glob("*.sql"))
        
        logger.info(f"Running {len(sql_files)} migration files...")
        
        for sql_file in sql_files:
            logger.info(f"Executing {sql_file.name}...")
            with open(sql_file, 'r') as f:
                sql_content = f.read()
            
            with db.connect() as conn, conn.cursor() as cur:
                cur.execute(sql_content)
            
            logger.info(f"✅ {sql_file.name} completed")
        
        logger.info("🎉 All migrations completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import fastapi
        import uvicorn
        logger.info("✅ FastAPI dependencies found")
        return True
    except ImportError as e:
        logger.error(f"❌ Missing dependencies: {e}")
        logger.info("Please install FastAPI dependencies:")
        logger.info("poetry add fastapi uvicorn[standard]")
        return False


def start_server(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    """Start the FastAPI server."""
    try:
        import uvicorn
        
        logger.info(f"🚀 Starting MemFuse API server on {host}:{port}")
        logger.info(f"📖 API docs will be available at http://{host}:{port}/docs")
        
        uvicorn.run(
            "memfuse.api_server:app",
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        raise


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Start MemFuse API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    parser.add_argument("--skip-migration", action="store_true", help="Skip database migration")
    
    args = parser.parse_args()
    
    print("🔧 MemFuse API Server Startup")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Run migrations unless skipped
    if not args.skip_migration:
        print("\n📊 Running database migrations...")
        if not run_database_migrations():
            sys.exit(1)
    else:
        print("\n⏭️  Skipping database migrations")
    
    # Start server
    print(f"\n🚀 Starting API server...")
    try:
        start_server(
            host=args.host,
            port=args.port,
            reload=not args.no_reload
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"\n❌ Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
