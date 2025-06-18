# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.8] - 2025-01-18

### Fixed
- Fixed middleware crash when using `app.mount()` for static files or other mounted applications
- Added workaround documentation for uvloop compatibility issues

### Changed
- Improved error handling for Mount objects in middleware route matching
- Enhanced troubleshooting documentation

## [0.1.0] - 2025-01-07

### Added
- Initial release of fastapi-x402
- `@pay()` decorator for adding payment requirements to FastAPI endpoints
- `init_x402()` function for setting up payment middleware
- Support for x402 protocol with USDC payments on Base Sepolia
- Automatic payment verification and settlement
- Replay protection for payments
- Comprehensive test suite
- Integration with x402 facilitators
- Support for custom facilitator URLs
- TypeScript client compatibility
- Example applications and documentation

### Features
- **One-liner integration**: Just add `@pay("$0.01")` to any endpoint
- **Real blockchain settlement**: Automatic USDC settlement on Base network
- **Cryptographic security**: Replay protection and signature verification
- **Standard protocol**: Built on x402 payment standard
- **Production ready**: Comprehensive testing and error handling

### Supported Networks
- Base Sepolia (testnet)

### Supported Assets  
- USDC (0x036CbD53842c5426634e7929541eC2318f3dCF7e on Base Sepolia)

[unreleased]: https://github.com/fastapi-x402/fastapi-x402/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/fastapi-x402/fastapi-x402/releases/tag/v0.1.0
