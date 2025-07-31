# NightScoutMongoBackup

[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=dustin-lennon_NightScoutMongoBackup&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=dustin-lennon_NightScoutMongoBackup) [![Code Smells](https://sonarcloud.io/api/project_badges/measure?project=dustin-lennon_NightScoutMongoBackup&metric=code_smells)](https://sonarcloud.io/summary/new_code?id=dustin-lennon_NightScoutMongoBackup) [![Coverage](https://sonarcloud.io/api/project_badges/measure?project=dustin-lennon_NightScoutMongoBackup&metric=coverage)](https://sonarcloud.io/summary/new_code?id=dustin-lennon_NightScoutMongoBackup) [![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=dustin-lennon_NightScoutMongoBackup&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=dustin-lennon_NightScoutMongoBackup) [![Vulnerabilities](https://sonarcloud.io/api/project_badges/measure?project=dustin-lennon_NightScoutMongoBackup&metric=vulnerabilities)](https://sonarcloud.io/summary/new_code?id=dustin-lennon_NightScoutMongoBackup)

This repository establishes a Discord bot that provides comprehensive backup functionality for NightScout MongoDB databases. Features include automated nightly backups, manual backup commands, and complete workflow integration with Discord threads and AWS S3 storage.

## Features

- **Automated Nightly Backups**: Scheduled backups with configurable timing
- **Manual Backup Commands**: Discord slash commands for on-demand backups
- **Cross-Platform Compression**: Support for gzip and Brotli compression algorithms
- **Discord Integration**: Real-time progress updates via Discord threads
- **AWS S3 Storage**: Secure cloud storage with public download links
- **MongoDB Atlas Compatible**: Designed specifically for MongoDB Atlas databases

## Compression Options

The bot supports two compression methods, both fully cross-platform compatible:

### Gzip (Recommended - Default)
- **Compression**: 70-80% size reduction for JSON data
- **Speed**: Fast compression and decompression
- **Compatibility**: Universal support across all platforms and tools
- **File Extension**: `.gz`

### Brotli (Better Compression)
- **Compression**: 85-95% size reduction for JSON data  
- **Speed**: Slightly slower than gzip but still efficient
- **Compatibility**: Modern cross-platform support
- **File Extension**: `.br`

Set `COMPRESSION_METHOD=brotli` in your environment file to use Brotli compression.

**Why not 7z?** While 7z offers excellent compression, it requires platform-specific binaries and external dependencies. Our native Node.js compression options provide excellent results with perfect cross-platform reliability.

## Testing

The project includes comprehensive test coverage with both unit and integration tests.

### Test Coverage: 87.09% ⭐

- **161 unit tests** covering all core functionality
- **3 integration tests** for AWS S3 connectivity (optional)
- **19 test suites** across all modules

### Running Tests

```bash
# Run all unit tests
npm test

# Run tests with coverage report
npm test -- --coverage

# Run specific test suite
npm test src/tests/s3Service.spec.ts
```

### S3 Integration Tests

The S3Service includes optional integration tests that validate real AWS connectivity:

```bash
# Set AWS credentials (integration tests will run automatically)
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export S3_BACKUP_BUCKET="your-test-bucket"

# Run S3 tests with integration validation
./scripts/test-s3-integration.sh
```

**Integration tests validate:**
- ✅ AWS credential authentication
- ✅ S3 bucket access and permissions  
- ✅ Complete file upload/download workflow
- ✅ Error handling for auth failures

See [S3_INTEGRATION_TESTING.md](docs/S3_INTEGRATION_TESTING.md) for detailed documentation.

A full README will be provided as development progresses.

```
