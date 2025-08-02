import { FileService } from '#lib/services/file';
import * as fs from 'fs/promises';
import * as path from 'path';
import { Document } from 'mongodb';
import { container } from '@sapphire/framework';

// Mock dependencies
jest.mock('fs/promises');
jest.mock('path');

// Mock the container
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

const mockAccess = fs.access as jest.MockedFunction<typeof fs.access>;
const mockMkdir = fs.mkdir as jest.MockedFunction<typeof fs.mkdir>;
const mockWriteFile = fs.writeFile as jest.MockedFunction<typeof fs.writeFile>;
const mockUnlink = fs.unlink as jest.MockedFunction<typeof fs.unlink>;
const mockRm = fs.rm as jest.MockedFunction<typeof fs.rm>;
const mockPathJoin = path.join as jest.MockedFunction<typeof path.join>;

// Mock console.error to prevent test output pollution
const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

describe('FileService', () => {
	let fileService: FileService;

	beforeEach(() => {
		// Reset all mocks
		jest.clearAllMocks();

		// Setup default mock implementations
		mockPathJoin.mockImplementation((...args) => args.join('/'));
		jest.spyOn(process, 'cwd').mockReturnValue('/app');

		// Create service instance
		fileService = new FileService();
	});

	afterEach(() => {
		consoleSpy.mockClear();
	});

	afterAll(() => {
		consoleSpy.mockRestore();
	});

	describe('constructor', () => {
		it('should initialize FileService', () => {
			expect(fileService).toBeInstanceOf(FileService);
		});

		it('should set correct backup directory', () => {
			expect(fileService.getBackupDirectory()).toBe('/app/backups');
		});
	});

	describe('ensureBackupDirectory', () => {
		it('should do nothing if directory already exists', async () => {
			mockAccess.mockResolvedValue(undefined);

			await fileService.ensureBackupDirectory();

			expect(mockAccess).toHaveBeenCalledWith('/app/backups');
			expect(mockMkdir).not.toHaveBeenCalled();
		});

		it('should create directory if it does not exist', async () => {
			mockAccess.mockRejectedValue(new Error('Directory not found'));
			mockMkdir.mockResolvedValue(undefined);

			await fileService.ensureBackupDirectory();

			expect(mockAccess).toHaveBeenCalledWith('/app/backups');
			expect(mockMkdir).toHaveBeenCalledWith('/app/backups', { mode: 0o775, recursive: true });
		});
	});

	describe('writeBackupData', () => {
		const mockTimestamp = new Date('2024-01-15T10:30:45.123Z');
		const mockData: Record<string, Document[]> = {
			collection1: [
				{ _id: '1', name: 'doc1' },
				{ _id: '2', name: 'doc2' }
			],
			collection2: [
				{ _id: '3', name: 'doc3' }
			]
		};

		beforeEach(() => {
			mockAccess.mockResolvedValue(undefined); // Directory exists
			mockWriteFile.mockResolvedValue(undefined);
		});

		it('should write backup data successfully', async () => {
			const result = await fileService.writeBackupData(mockData, mockTimestamp);

			expect(mockAccess).toHaveBeenCalledWith('/app/backups');
			expect(mockWriteFile).toHaveBeenCalledWith(
				'/app/backups/nightscout-backup-2024-01-15T10-30-45-123Z.json',
				expect.any(String),
				{ mode: 0o664 }
			);

			// Verify the content structure
			const writeCall = mockWriteFile.mock.calls[0];
			const backupContent = JSON.parse(writeCall[1] as string);
			expect(backupContent.timestamp).toBe('2024-01-15T10:30:45.123Z');
			expect(backupContent.collections).toEqual(mockData);

			expect(result).toEqual({
				success: true,
				filePath: '/app/backups/nightscout-backup-2024-01-15T10-30-45-123Z.json'
			});
		});

		it('should include correct metadata in backup content', async () => {
			await fileService.writeBackupData(mockData, mockTimestamp);

			const writeCall = mockWriteFile.mock.calls[0];
			const backupContent = JSON.parse(writeCall[1] as string);

			expect(backupContent).toEqual({
				timestamp: '2024-01-15T10:30:45.123Z',
				collections: mockData,
				metadata: {
					totalCollections: 2,
					totalDocuments: 3
				}
			});
		});

		it('should create backup directory if it does not exist', async () => {
			mockAccess.mockRejectedValue(new Error('Directory not found'));
			mockMkdir.mockResolvedValue(undefined);

			const result = await fileService.writeBackupData(mockData, mockTimestamp);

			expect(mockMkdir).toHaveBeenCalledWith('/app/backups', { mode: 0o775, recursive: true });
			expect(result.success).toBe(true);
		});

		it('should handle write errors', async () => {
			mockWriteFile.mockRejectedValue(new Error('Write failed'));

			const result = await fileService.writeBackupData(mockData, mockTimestamp);

			expect(result).toEqual({
				success: false,
				error: 'Write failed'
			});
		});

		it('should handle directory creation errors', async () => {
			mockAccess.mockRejectedValue(new Error('Directory not found'));
			mockMkdir.mockRejectedValue(new Error('Permission denied'));

			const result = await fileService.writeBackupData(mockData, mockTimestamp);

			expect(result).toEqual({
				success: false,
				error: 'Permission denied'
			});
		});

		it('should handle empty collections', async () => {
			const emptyData: Record<string, Document[]> = {};

			const result = await fileService.writeBackupData(emptyData, mockTimestamp);

			expect(result.success).toBe(true);
			const writeCall = mockWriteFile.mock.calls[0];
			const backupContent = JSON.parse(writeCall[1] as string);
			expect(backupContent.metadata).toEqual({
				totalCollections: 0,
				totalDocuments: 0
			});
		});
	});

	describe('deleteFile', () => {
		it('should delete file successfully', async () => {
			mockUnlink.mockResolvedValue(undefined);

			await fileService.deleteFile('/path/to/file.json');

			expect(mockUnlink).toHaveBeenCalledWith('/path/to/file.json');
			expect(consoleSpy).not.toHaveBeenCalled();
		});

		it('should handle delete errors gracefully', async () => {
			mockUnlink.mockRejectedValue(new Error('File not found'));

			await fileService.deleteFile('/path/to/file.json');

			expect(mockUnlink).toHaveBeenCalledWith('/path/to/file.json');
			expect(container.logger.error).toHaveBeenCalledWith(
				'Failed to delete file /path/to/file.json:',
				expect.any(Error)
			);
		});
	});

	describe('deleteDirectory', () => {
		it('should delete directory successfully', async () => {
			mockRm.mockResolvedValue(undefined);

			await fileService.deleteDirectory('/path/to/directory');

			expect(mockRm).toHaveBeenCalledWith('/path/to/directory', { recursive: true, force: true });
			expect(consoleSpy).not.toHaveBeenCalled();
		});

		it('should handle delete errors gracefully', async () => {
			mockRm.mockRejectedValue(new Error('Directory not found'));

			await fileService.deleteDirectory('/path/to/directory');

			expect(mockRm).toHaveBeenCalledWith('/path/to/directory', { recursive: true, force: true });
			expect(container.logger.error).toHaveBeenCalledWith(
				'Failed to delete directory /path/to/directory:',
				expect.any(Error)
			);
		});
	});

	describe('getBackupDirectory', () => {
		it('should return the correct backup directory path', () => {
			expect(fileService.getBackupDirectory()).toBe('/app/backups');
		});
	});
});
