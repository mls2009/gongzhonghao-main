# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Application Overview

This is a WeChat Official Account and social media auto-publishing system, originally designed for Windows and now fully adapted for macOS. The system manages content materials, social media accounts, and automates publishing workflows across multiple platforms including WeChat Official Accounts, Toutiao, and Xiaohongshu.

## Development Commands

### Setup and Installation
```bash
# Quick start (recommended)
chmod +x start_macos.sh
./start_macos.sh

# Manual setup
pip3 install -r requirements.txt
playwright install
python3 app/init_db.py
cd app && python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Database Management
```bash
# Initialize database with sample data
python3 app/init_db.py

# Update database structure (preserves data)
python3 app/init_db.py --update

# Test specific functions
python3 test_clear_function.py
python3 fix_publish_status.py
```

### Testing and Development
- **Web Interface**: http://localhost:8000
- **BitBrowser API**: Required to run on port 54345 for browser automation
- **Database**: SQLite database at `wechat_matrix.db`

## Architecture Overview

### Core Components

**FastAPI Application** (`app/main.py`):
- Main application entry point with router registration
- Auto-scans materials directory on startup
- Integrates with BitBrowser API for browser automation
- Implements background task scheduling

**Database Models** (`app/models/database.py`):
- SQLAlchemy ORM with SQLite backend
- Key tables: Account, Material, Browser, Settings, XiaohongshuMaterial, ImageTemplate
- Supports multiple platform types and publishing states

**Router Architecture** (`app/routers/`):
- Modular API endpoints organized by functionality
- `settings.py`: Cross-platform folder selection with AppleScript/PowerShell
- `materials.py`: Content management and publishing workflows
- `accounts.py`, `browsers.py`: Account and browser management
- Platform-specific routers for Xiaohongshu and template materials

### Key Features

**Cross-Platform Compatibility**:
- macOS: AppleScript for native folder dialogs
- Windows: PowerShell folder browser
- Linux: tkinter fallback

**Material Management**:
- Auto-scans .docx files from configured directory
- Tracks word count, image count, and publishing status
- Supports scheduled publishing with background tasks

**Browser Integration**:
- BitBrowser API integration for automated publishing
- Playwright fallback for standard browser automation
- Multi-account support with browser profile management

**Publishing Workflow**:
- Supports WeChat Official Accounts and Toutiao
- Scheduled publishing with APScheduler
- Status tracking (unpublished, published, scheduled, failed)

### Database Schema

**Core Tables**:
- `accounts`: User accounts with browser associations
- `materials`: Content items with publishing metadata
- `settings`: System configuration (materials path, scan history)
- `xiaohongshu_materials`: Platform-specific content for Xiaohongshu
- `image_templates`, `content_templates`: Template management

### External Dependencies

**Required Services**:
- BitBrowser running on port 54345 for browser automation
- Materials directory with .docx files

**Key Libraries**:
- FastAPI/Uvicorn for web framework
- SQLAlchemy/SQLite for database
- Playwright for browser automation
- APScheduler for background tasks
- python-docx for document processing

## Platform-Specific Notes

### macOS Adaptations
- AppleScript folder dialogs in `app/routers/settings.py:29-42`
- Virtual environment activation in startup script
- Cross-platform path handling throughout codebase

### BitBrowser Integration
- Fixed token configuration (do not modify)
- API endpoint: `http://127.0.0.1:54345`
- Browser profile management for multi-account support

## Common Development Tasks

### Adding New Platform Support
1. Create new router in `app/routers/`
2. Add platform-specific models to `app/models/database.py`
3. Register router in `app/main.py`
4. Add corresponding HTML templates

### Material Processing Workflow
1. Materials auto-scanned from configured directory on startup
2. Word documents parsed for content, word count, image count
3. Publishing handled through platform-specific routers
4. Status tracked through Material model states

### Scheduled Publishing
- Background scheduler in `app/scheduler/publish_scheduler.py`
- Checks for scheduled materials every minute when tasks pending
- Updates to every 30 minutes when no scheduled tasks