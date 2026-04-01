# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.3] - 2026-04-01

### Added

- Added `.env` file management support.
- Improved the project structure for better organization and maintainability.

## [1.1.2] - 2026-03-14

### Added

- **Two-Factor Authentication (2FA)**: Added support for TOTP-based secondary authentication for enhanced vault security.
- **Entry Editing**: Added the ability to edit existing password, card, and note entries.
- **Project Restructuring**: Organized source code into `src/` directory and assets into `assets/`.
- **New Entry Point**: Added `main.py` in the root directory for standard application startup.
- **Version Display**: The application version is now displayed in the main window title bar.

### Fixed

- Updated `SafeVault.spec` to support the new project structure.
- Improved `README.md` with detailed project structure and updated instructions.
- Optimized backend version management.
