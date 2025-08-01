import { createReadStream, createWriteStream } from 'fs';
import { pipeline } from 'stream/promises';
import { createGzip, createBrotliCompress, constants } from 'zlib';
import * as fs from 'fs/promises';

export interface CompressionResult {
	success: boolean;
	compressedPath?: string;
	originalSize?: number;
	compressedSize?: number;
	compressionType?: 'gzip' | 'brotli';
	error?: string;
}

export class CompressionService {
	/**
	 * Compress file using gzip (recommended for cross-platform compatibility)
	 */
	async compressFile(filePath: string): Promise<CompressionResult> {
		return this.compressWithGzip(filePath);
	}

	/**
	 * Compress file using gzip compression
	 */
	async compressWithGzip(filePath: string): Promise<CompressionResult> {
		try {
			const compressedPath = `${filePath}.gz`;

			// Get original file size
			const stats = await fs.stat(filePath);
			const originalSize = stats.size;

			// Create compression stream
			const source = createReadStream(filePath);
			const destination = createWriteStream(compressedPath, { mode: 0o664 });
			const gzip = createGzip({ level: 9 }); // Maximum compression

			// Compress the file
			await pipeline(source, gzip, destination);

			// Get compressed file size
			const compressedStats = await fs.stat(compressedPath);
			const compressedSize = compressedStats.size;

			return {
				success: true,
				compressedPath,
				originalSize,
				compressedSize,
				compressionType: 'gzip'
			};
		} catch (error) {
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Unknown gzip compression error'
			};
		}
	}

	/**
	 * Compress file using Brotli compression (better compression ratio, still cross-platform)
	 */
	async compressWithBrotli(filePath: string): Promise<CompressionResult> {
		try {
			const compressedPath = `${filePath}.br`;

			// Get original file size
			const stats = await fs.stat(filePath);
			const originalSize = stats.size;

			// Create compression stream
			const source = createReadStream(filePath);
			const destination = createWriteStream(compressedPath, { mode: 0o664 });
			const brotli = createBrotliCompress({
				params: {
					// Maximum compression quality
					[constants.BROTLI_PARAM_QUALITY]: 11,
					// Text mode for better JSON compression
					[constants.BROTLI_PARAM_MODE]: constants.BROTLI_MODE_TEXT
				}
			});

			// Compress the file
			await pipeline(source, brotli, destination);

			// Get compressed file size
			const compressedStats = await fs.stat(compressedPath);
			const compressedSize = compressedStats.size;

			return {
				success: true,
				compressedPath,
				originalSize,
				compressedSize,
				compressionType: 'brotli'
			};
		} catch (error) {
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Unknown brotli compression error'
			};
		}
	}

	formatSize(bytes: number): string {
		const units = ['B', 'KB', 'MB', 'GB'];
		let size = bytes;
		let unitIndex = 0;

		while (size >= 1024 && unitIndex < units.length - 1) {
			size /= 1024;
			unitIndex++;
		}

		return `${size.toFixed(2)} ${units[unitIndex]}`;
	}

	calculateCompressionRatio(originalSize: number, compressedSize: number): string {
		const ratio = ((originalSize - compressedSize) / originalSize) * 100;
		return `${ratio.toFixed(1)}%`;
	}
}

export const compressionService = new CompressionService();
