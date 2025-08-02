import { CompressionService } from '#lib/services/compression';
import * as fs from 'fs/promises';
import { createReadStream, createWriteStream } from 'fs';
import { pipeline } from 'stream/promises';
import { createGzip, createBrotliCompress } from 'zlib';

// Mock dependencies
jest.mock('fs/promises');
jest.mock('fs');
jest.mock('stream/promises');
jest.mock('zlib');

const mockStat = fs.stat as jest.MockedFunction<typeof fs.stat>;
const mockCreateReadStream = createReadStream as jest.MockedFunction<typeof createReadStream>;
const mockCreateWriteStream = createWriteStream as jest.MockedFunction<typeof createWriteStream>;
const mockPipeline = pipeline as jest.MockedFunction<typeof pipeline>;
const mockCreateGzip = createGzip as jest.MockedFunction<typeof createGzip>;
const mockCreateBrotliCompress = createBrotliCompress as jest.MockedFunction<typeof createBrotliCompress>;

describe('CompressionService', () => {
	let compressionService: CompressionService;
	const originalEnv = process.env;

	beforeEach(() => {
		// Reset environment
		process.env = {
			...originalEnv,
			COMPRESSION_METHOD: 'gzip'
		};

		// Reset all mocks
		jest.clearAllMocks();

		// Setup default mock implementations
		mockStat.mockResolvedValue({ size: 1024 } as any);

		const mockReadStream = { pipe: jest.fn() } as any;
		const mockWriteStream = { write: jest.fn() } as any;
		const mockGzipStream = { pipe: jest.fn() } as any;
		const mockBrotliStream = { pipe: jest.fn() } as any;

		mockCreateReadStream.mockReturnValue(mockReadStream);
		mockCreateWriteStream.mockReturnValue(mockWriteStream);
		mockCreateGzip.mockReturnValue(mockGzipStream);
		mockCreateBrotliCompress.mockReturnValue(mockBrotliStream);
		mockPipeline.mockResolvedValue(undefined);

		// Create service instance
		compressionService = new CompressionService();
	});

	afterEach(() => {
		process.env = originalEnv;
	});

	describe('constructor', () => {
		it('should initialize CompressionService', () => {
			expect(compressionService).toBeInstanceOf(CompressionService);
		});
	});

	describe('compressFile', () => {
		it('should compress file using gzip (default method)', async () => {
			// Mock two stat calls: original file and compressed file
			mockStat
				.mockResolvedValueOnce({ size: 2048 } as any) // Original file
				.mockResolvedValueOnce({ size: 1024 } as any); // Compressed file

			const result = await compressionService.compressFile('/path/to/input.json');

			expect(mockCreateReadStream).toHaveBeenCalledWith('/path/to/input.json');
			expect(mockCreateWriteStream).toHaveBeenCalledWith('/path/to/input.json.gz', { mode: 0o664 });
			expect(mockCreateGzip).toHaveBeenCalledWith({ level: 9 });
			expect(mockPipeline).toHaveBeenCalled();
			expect(result).toEqual({
				success: true,
				compressedPath: '/path/to/input.json.gz',
				originalSize: 2048,
				compressedSize: 1024,
				compressionType: 'gzip'
			});
		});

		it('should handle compression errors', async () => {
			mockStat.mockResolvedValueOnce({ size: 1024 } as any);
			mockPipeline.mockRejectedValue(new Error('Compression failed'));

			const result = await compressionService.compressFile('/path/to/input.json');

			expect(result).toEqual({
				success: false,
				error: 'Compression failed'
			});
		});

		it('should handle file stat errors', async () => {
			mockStat.mockRejectedValue(new Error('File not found'));

			const result = await compressionService.compressFile('/nonexistent/file.json');

			expect(result).toEqual({
				success: false,
				error: 'File not found'
			});
		});
	});

	describe('compressWithBrotli', () => {
		it('should compress file using brotli compression', async () => {
			mockStat
				.mockResolvedValueOnce({ size: 2048 } as any) // Original file
				.mockResolvedValueOnce({ size: 512 } as any); // Compressed file

			const result = await compressionService.compressWithBrotli('/path/to/input.json');

			expect(mockCreateReadStream).toHaveBeenCalledWith('/path/to/input.json');
			expect(mockCreateWriteStream).toHaveBeenCalledWith('/path/to/input.json.br', { mode: 0o664 });
			expect(mockCreateBrotliCompress).toHaveBeenCalled();
			expect(mockPipeline).toHaveBeenCalled();
			expect(result).toEqual({
				success: true,
				compressedPath: '/path/to/input.json.br',
				originalSize: 2048,
				compressedSize: 512,
				compressionType: 'brotli'
			});
		});

		it('should handle brotli compression errors', async () => {
			mockStat.mockResolvedValueOnce({ size: 1024 } as any);
			mockPipeline.mockRejectedValue(new Error('Brotli compression failed'));

			const result = await compressionService.compressWithBrotli('/path/to/input.json');

			expect(result).toEqual({
				success: false,
				error: 'Brotli compression failed'
			});
		});
	});

	describe('utility methods', () => {
		it('should format file sizes correctly', () => {
			expect(compressionService.formatSize(1024)).toBe('1.00 KB');
			expect(compressionService.formatSize(1048576)).toBe('1.00 MB');
			expect(compressionService.formatSize(500)).toBe('500.00 B');
			expect(compressionService.formatSize(1073741824)).toBe('1.00 GB');
		});

		it('should calculate compression ratio correctly', () => {
			expect(compressionService.calculateCompressionRatio(1000, 500)).toBe('50.0%');
			expect(compressionService.calculateCompressionRatio(2000, 1000)).toBe('50.0%');
			expect(compressionService.calculateCompressionRatio(1000, 0)).toBe('100.0%');
			expect(compressionService.calculateCompressionRatio(1000, 1000)).toBe('0.0%');
		});
	});
});
