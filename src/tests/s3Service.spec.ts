// Mock the container before other imports to prevent filesystem scanning issues
jest.mock('@sapphire/framework', () => ({
	container: {
		logger: {
			error: jest.fn(),
			info: jest.fn(),
			warn: jest.fn(),
			debug: jest.fn()
		}
	}
}));

import { S3Service } from '../lib/services/s3';
import { S3Client, PutObjectCommand, DeleteObjectCommand, ListObjectsV2Command } from '@aws-sdk/client-s3';
import { createReadStream } from 'fs';
import * as fsPromises from 'fs/promises';
import { container } from '@sapphire/framework';

// Mock AWS SDK
jest.mock('@aws-sdk/client-s3', () => ({
	S3Client: jest.fn(),
	PutObjectCommand: jest.fn(),
	DeleteObjectCommand: jest.fn(),
	ListObjectsV2Command: jest.fn()
}));

// Mock fs modules
jest.mock('fs/promises');
jest.mock('fs', () => ({
	createReadStream: jest.fn()
}));

const mockS3ClientInstance = {
	send: jest.fn()
};

const MockedS3Client = jest.mocked(S3Client);
const MockedPutObjectCommand = jest.mocked(PutObjectCommand);
const MockedDeleteObjectCommand = jest.mocked(DeleteObjectCommand);
const mockedFsPromises = jest.mocked(fsPromises);
const mockedCreateReadStream = jest.mocked(createReadStream);

describe('S3Service', () => {
	let s3Service: S3Service;

	beforeEach(() => {
		jest.clearAllMocks();

		// Setup AWS SDK mocks
		MockedS3Client.mockImplementation(() => mockS3ClientInstance as any);
		MockedPutObjectCommand.mockImplementation((params) => params as any);
		MockedDeleteObjectCommand.mockImplementation((params) => params as any);

		// Setup environment variables
		process.env.AWS_REGION = 'us-east-1';
		process.env.S3_BACKUP_BUCKET = 'test-bucket';
		process.env.AWS_ACCESS_KEY_ID = 'test-access-key';
		process.env.AWS_SECRET_ACCESS_KEY = 'test-secret-key';

		s3Service = new S3Service();
	});

	afterEach(() => {
		delete process.env.AWS_REGION;
		delete process.env.S3_BACKUP_BUCKET;
		delete process.env.AWS_ACCESS_KEY_ID;
		delete process.env.AWS_SECRET_ACCESS_KEY;
	});

	describe('constructor', () => {
		it('should initialize with environment variables', () => {
			expect(MockedS3Client).toHaveBeenCalledWith({
				region: 'us-east-1',
				credentials: {
					accessKeyId: 'test-access-key',
					secretAccessKey: 'test-secret-key'
				}
			});
		});

		it('should use default values when environment variables are missing', () => {
			delete process.env.AWS_REGION;
			delete process.env.S3_BACKUP_BUCKET;
			delete process.env.AWS_ACCESS_KEY_ID;
			delete process.env.AWS_SECRET_ACCESS_KEY;

			new S3Service();

			expect(MockedS3Client).toHaveBeenCalledWith({
				region: 'us-east-1',
				credentials: {
					accessKeyId: '',
					secretAccessKey: ''
				}
			});
		});
	});

	describe('getBucketName', () => {
		it('should return the configured bucket name', () => {
			expect(s3Service.getBucketName()).toBe('test-bucket');
		});
	});

	describe('getRegion', () => {
		it('should return the configured region', () => {
			expect(s3Service.getRegion()).toBe('us-east-1');
		});
	});

	describe('uploadFile', () => {
		const mockFileStream = { pipe: jest.fn() };
		const mockFileStats = {
			size: 1024,
			isFile: () => true,
			isDirectory: () => false,
			isSymbolicLink: () => false,
			atimeMs: Date.now(),
			mtimeMs: Date.now(),
			ctimeMs: Date.now(),
			birthtimeMs: Date.now(),
			atime: new Date(),
			mtime: new Date(),
			ctime: new Date(),
			birthtime: new Date(),
			blksize: 4096,
			blocks: 8,
			mode: parseInt('644', 8),
			nlink: 1,
			uid: 1000,
			gid: 1000,
			rdev: 0,
			ino: 123456,
			dev: 2048
		};

		beforeEach(() => {
			mockedCreateReadStream.mockReturnValue(mockFileStream as any);
			mockedFsPromises.stat.mockResolvedValue(mockFileStats as any);
			mockS3ClientInstance.send.mockResolvedValue({});
		});

		it('should successfully upload a JSON file', async () => {
			const filePath = '/path/to/test.json';

			const result = await s3Service.uploadFile(filePath);

			expect(result.success).toBe(true);
			expect(result.s3Url).toContain('https://test-bucket.s3.us-east-1.amazonaws.com/');
			expect(result.key).toMatch(/^backups\/\d{4}-\d{2}-\d{2}\/test\.json$/);
			expect(result.bucket).toBe('test-bucket');

			expect(mockedFsPromises.stat).toHaveBeenCalledWith(filePath);
			expect(mockedCreateReadStream).toHaveBeenCalledWith(filePath);
			expect(MockedPutObjectCommand).toHaveBeenCalledWith({
				Bucket: 'test-bucket',
				Key: expect.stringMatching(/^backups\/\d{4}-\d{2}-\d{2}\/test\.json$/),
				Body: mockFileStream,
				ContentLength: 1024,
				ContentType: 'application/json',
				ACL: 'public-read',
				Metadata: {
					'backup-timestamp': expect.any(String),
					'file-size': '1024'
				}
			});
		});

		it('should successfully upload a gzipped file', async () => {
			const filePath = '/path/to/test.gz';

			const result = await s3Service.uploadFile(filePath);

			expect(result.success).toBe(true);
			expect(result.key).toMatch(/^backups\/\d{4}-\d{2}-\d{2}\/test\.gz$/);
			expect(MockedPutObjectCommand).toHaveBeenCalledWith(
				expect.objectContaining({
					ContentType: 'application/gzip'
				})
			);
		});

		it('should successfully upload a brotli compressed file', async () => {
			const filePath = '/path/to/test.br';

			const result = await s3Service.uploadFile(filePath);

			expect(result.success).toBe(true);
			expect(result.key).toMatch(/^backups\/\d{4}-\d{2}-\d{2}\/test\.br$/);
			expect(MockedPutObjectCommand).toHaveBeenCalledWith(
				expect.objectContaining({
					ContentType: 'application/brotli'
				})
			);
		});

		it('should successfully upload a 7z compressed file', async () => {
			const filePath = '/path/to/test.7z';

			const result = await s3Service.uploadFile(filePath);

			expect(result.success).toBe(true);
			expect(result.key).toMatch(/^backups\/\d{4}-\d{2}-\d{2}\/test\.7z$/);
			expect(MockedPutObjectCommand).toHaveBeenCalledWith(
				expect.objectContaining({
					ContentType: 'application/x-7z-compressed'
				})
			);
		});

		it('should handle unknown file extensions', async () => {
			const filePath = '/path/to/test.unknown';

			const result = await s3Service.uploadFile(filePath);

			expect(result.success).toBe(true);
			expect(MockedPutObjectCommand).toHaveBeenCalledWith(
				expect.objectContaining({
					ContentType: 'application/octet-stream'
				})
			);
		});

		it('should handle file stat errors', async () => {
			const filePath = '/path/to/nonexistent.json';
			mockedFsPromises.stat.mockRejectedValueOnce(new Error('File not found'));

			const result = await s3Service.uploadFile(filePath);

			expect(result.success).toBe(false);
			expect(result.error).toContain('File not found');
		});

		it('should handle S3 upload errors', async () => {
			const filePath = '/path/to/test.json';
			mockS3ClientInstance.send.mockRejectedValueOnce(new Error('S3 upload failed'));

			const result = await s3Service.uploadFile(filePath);

			expect(result.success).toBe(false);
			expect(result.error).toContain('S3 upload failed');
		});

		it('should handle non-Error exceptions', async () => {
			const filePath = '/path/to/test.json';
			mockS3ClientInstance.send.mockRejectedValueOnce('String error');

			const result = await s3Service.uploadFile(filePath);

			expect(result.success).toBe(false);
			expect(result.error).toBe('Unknown S3 upload error');
		});

		it('should create correct upload parameters', async () => {
			const filePath = '/path/to/backup.json';

			await s3Service.uploadFile(filePath);

			expect(MockedPutObjectCommand).toHaveBeenCalledWith({
				Bucket: 'test-bucket',
				Key: expect.stringMatching(/^backups\/\d{4}-\d{2}-\d{2}\/backup\.json$/),
				Body: mockFileStream,
				ContentLength: 1024,
				ContentType: 'application/json',
				ACL: 'public-read',
				Metadata: {
					'backup-timestamp': expect.any(String),
					'file-size': '1024'
				}
			});
		});
	});

	describe('deleteObject', () => {
		it('should successfully delete an object', async () => {
			const key = 'backups/2023-12-01/test.json';
			mockS3ClientInstance.send.mockResolvedValueOnce({});

			await s3Service.deleteObject(key);

			expect(MockedDeleteObjectCommand).toHaveBeenCalledWith({
				Bucket: 'test-bucket',
				Key: key
			});
			expect(mockS3ClientInstance.send).toHaveBeenCalled();
		});

		it('should handle delete errors gracefully', async () => {
			const key = 'backups/2023-12-01/test.json';
			mockS3ClientInstance.send.mockRejectedValueOnce(new Error('Delete failed'));

			await s3Service.deleteObject(key);

			expect(container.logger.error).toHaveBeenCalledWith(
				`Failed to delete S3 object ${key}:`,
				expect.any(Error)
			);
		});
	});

	describe('getContentType', () => {
		it('should return correct content types for different file extensions', async () => {
			// Test private method through upload which calls it
			const testCases = [
				{ file: 'test.json', expectedType: 'application/json' },
				{ file: 'test.gz', expectedType: 'application/gzip' },
				{ file: 'test.br', expectedType: 'application/brotli' },
				{ file: 'test.7z', expectedType: 'application/x-7z-compressed' },
				{ file: 'test.unknown', expectedType: 'application/octet-stream' }
			];

			for (const testCase of testCases) {
				jest.clearAllMocks();
				mockedCreateReadStream.mockReturnValue({ pipe: jest.fn() } as any);
				mockedFsPromises.stat.mockResolvedValue({
					size: 100,
					isFile: () => true,
					isDirectory: () => false,
					isSymbolicLink: () => false,
					atimeMs: Date.now(),
					mtimeMs: Date.now(),
					ctimeMs: Date.now(),
					birthtimeMs: Date.now(),
					atime: new Date(),
					mtime: new Date(),
					ctime: new Date(),
					birthtime: new Date(),
					blksize: 4096,
					blocks: 8,
					mode: parseInt('644', 8),
					nlink: 1,
					uid: 1000,
					gid: 1000,
					rdev: 0,
					ino: 123456,
					dev: 2048
				} as any);
				mockS3ClientInstance.send.mockResolvedValue({});

				await s3Service.uploadFile(`/path/to/${testCase.file}`);

				expect(MockedPutObjectCommand).toHaveBeenCalledWith(
					expect.objectContaining({
						ContentType: testCase.expectedType
					})
				);
			}
		});
	});

	describe('listBackups', () => {
		it('should list backup files successfully', async () => {
			const mockResponse = {
				Contents: [
					{
						Key: 'backups/2025-07-30/backup-1.tar.gz',
						Size: 1048576,
						LastModified: new Date('2025-07-30T12:00:00Z'),
						ETag: '"abc123"',
						StorageClass: 'STANDARD'
					},
					{
						Key: 'backups/2025-07-29/backup-2.tar.gz',
						Size: 2097152,
						LastModified: new Date('2025-07-29T12:00:00Z'),
						ETag: '"def456"',
						StorageClass: 'STANDARD'
					}
				]
			};

			mockS3ClientInstance.send.mockResolvedValueOnce(mockResponse);

			const result = await s3Service.listBackups();

			expect(result.success).toBe(true);
			expect(result.files).toHaveLength(2);
			expect(result.totalFiles).toBe(2);

			// Check that files are sorted by date (newest first)
			expect(result.files[0].fileName).toBe('backup-1.tar.gz');
			expect(result.files[0].size).toBe(1048576);
			expect(result.files[0].etag).toBe('abc123');
			expect(result.files[0].downloadUrl).toContain('backup-1.tar.gz');

			expect(ListObjectsV2Command).toHaveBeenCalledWith({
				Bucket: 'test-bucket',
				Prefix: 'backups/',
				MaxKeys: 1000
			});
		});

		it('should handle empty bucket', async () => {
			const mockResponse = {
				Contents: []
			};

			mockS3ClientInstance.send.mockResolvedValueOnce(mockResponse);

			const result = await s3Service.listBackups();

			expect(result.success).toBe(true);
			expect(result.files).toHaveLength(0);
			expect(result.totalFiles).toBe(0);
		});

		it('should handle S3 errors', async () => {
			const error = new Error('Access Denied');
			mockS3ClientInstance.send.mockRejectedValueOnce(error);

			const result = await s3Service.listBackups();

			expect(result.success).toBe(false);
			expect(result.files).toHaveLength(0);
			expect(result.totalFiles).toBe(0);
			expect(result.error).toBe('Access Denied');
		});
	});
});
