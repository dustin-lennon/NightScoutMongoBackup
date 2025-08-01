import { s3Service } from '#lib/services/s3';
import { discordThreadService } from '#lib/services/discordThread';
import { envParseString } from '@skyra/env-utilities';
import { exec } from 'child_process';
import { promisify } from 'util';
import * as path from 'path';
import * as fs from 'fs/promises';
import { container } from '@sapphire/framework';
import {
	BaseBackupService,
	BackupOptions,
	BackupResult,
	BackupEventData
} from '#lib/services/backup-base';

export class BackupService extends BaseBackupService {
	private readonly execAsync = promisify(exec);

	private buildMongoUri(): string {
		const username = encodeURIComponent(envParseString('MONGO_USERNAME', ''));
		const password = encodeURIComponent(envParseString('MONGO_PASSWORD', ''));
		const host = envParseString('MONGO_HOST', '');
		const database = envParseString('MONGO_DB', '');

		return `mongodb+srv://${username}:${password}@${host}/${database}`;
	}

	override async performBackup(options: BackupOptions = {}): Promise<BackupResult> {
		const startTime = new Date();
		const backupId = this.generateBackupId();

		const result: BackupResult = this.createInitialResult(startTime);

		let threadId: string | undefined;
		let compressedPath: string | undefined;

		try {
			const collectionsToBackup = options.collections || this.defaultCollections;

			// Step 1: Create Discord thread if requested
			if (options.createThread) {
				const threadResult = await discordThreadService.createBackupThread(backupId);
				if (threadResult.success && threadResult.threadId) {
					threadId = threadResult.threadId;
					result.threadId = threadId;

					// Send start message
					await discordThreadService.sendBackupStartMessage(threadId, collectionsToBackup);
				}
			}

			// Step 2: Create MongoDB dump using mongodump
			if (threadId) {
				await discordThreadService.sendBackupProgressMessage(
					threadId,
					'Creating MongoDB Dump',
					'Using mongodump for complete database backup...'
				);
			}

			const mongoUri = this.buildMongoUri();
			const tempDir = `/tmp/nightscout-backup-${backupId}`;
			const dumpDir = path.join(tempDir, 'dump');

			// Ensure temp directory exists
			await fs.mkdir(tempDir, { recursive: true });

			// Build mongodump command
			const collectionFlags = collectionsToBackup.map(col => `--collection ${col}`).join(' ');
			const mongodumpCmd = `mongodump --uri "${mongoUri}" --out "${dumpDir}" ${collectionFlags}`;

			try {
				const { stdout, stderr } = await this.execAsync(mongodumpCmd);

			// Parse mongodump output to get document counts
			const dumpOutput = stdout + stderr;
			result.collectionsProcessed = collectionsToBackup;

			// Extract document count from mongodump output (approximate)
			// Use a more secure regex pattern to avoid backtracking vulnerabilities
			const documentMatches = dumpOutput.match(/(\d{1,10}) document/g);
			if (documentMatches) {
				result.totalDocumentsProcessed = documentMatches
					.map(match => {
						const numStr = match.replace(' document', '');
						return parseInt(numStr) || 0;
					})
					.reduce((sum, count) => sum + count, 0);
			}			} catch (mongodumpError) {
				throw new Error(`MongoDB dump failed: ${mongodumpError instanceof Error ? mongodumpError.message : 'Unknown error'}`);
			}

			// Step 3: Create tar.gz archive of the dump
			if (threadId) {
				await discordThreadService.sendBackupProgressMessage(
					threadId,
					'Compressing Backup',
					'Creating compressed archive of database dump...'
				);
			}

			const tarPath = path.join(tempDir, `nightscout-backup-${backupId}.tar.gz`);
			const tarCmd = `tar -czf "${tarPath}" -C "${dumpDir}" .`;

			try {
				await this.execAsync(tarCmd);
				compressedPath = tarPath;
				result.compressedPath = compressedPath;
			} catch (tarError) {
				throw new Error(`Archive creation failed: ${tarError instanceof Error ? tarError.message : 'Unknown error'}`);
			}

			// Step 4: Upload to S3
			if (threadId) {
				await discordThreadService.sendBackupProgressMessage(
					threadId,
					'Uploading to S3',
					'Uploading compressed backup to AWS S3...'
				);
			}

			const s3Result = await s3Service.uploadFile(compressedPath);
			if (!s3Result.success) {
				throw new Error(`S3 upload failed: ${s3Result.error}`);
			}
			result.s3Url = s3Result.s3Url!;

			// Step 5: Clean up local files
			await fs.rm(tempDir, { recursive: true, force: true });

			// Step 6: Mark as successful and send completion message
			result.success = true;
			result.timestamp = new Date();

			// Get file size for completion message and history
			let compressedSize: number | undefined;
			try {
				const stats = await fs.stat(compressedPath);
				compressedSize = stats.size;
			} catch {
				// File might be cleaned up already
			}

			if (threadId) {
				const duration = (result.timestamp.getTime() - startTime.getTime()) / 1000;

				await discordThreadService.sendBackupCompleteMessage(threadId, {
					collectionsProcessed: result.collectionsProcessed,
					totalDocuments: result.totalDocumentsProcessed,
					originalSize: undefined, // mongodump doesn't provide uncompressed size easily
					compressedSize,
					compressionRatio: undefined,
					s3Url: result.s3Url,
					duration
				});
			}

			// Step 7: Clean up local files after getting size
			await fs.rm(tempDir, { recursive: true, force: true });

			// Add to history for tracking
			this.addToHistory({
				timestamp: result.timestamp,
				collectionsProcessed: [...result.collectionsProcessed],
				totalDocumentsProcessed: result.totalDocumentsProcessed,
				success: true,
				s3Url: result.s3Url,
				size: compressedSize
			});

			// Emit backup completed event
			container.client.emit('backupCompleted', {
				filename: path.basename(compressedPath || ''),
				timestamp: result.timestamp,
				success: true,
				s3Url: result.s3Url,
				collections: result.collectionsProcessed,
				size: compressedSize
			} as BackupEventData);

		} catch (error) {
			result.error = error instanceof Error ? error.message : 'Unknown error occurred';

			// Emit backup failed event
			container.client.emit('backupFailed', {
				error: error instanceof Error ? error : new Error('Unknown error occurred'),
				operation: 'backup'
			});

			// Send error message to thread if available
			if (threadId) {
				await discordThreadService.sendBackupErrorMessage(threadId, result.error);
			}

			// Clean up files on error
			if (compressedPath) {
				try {
					const tempDir = path.dirname(compressedPath);
					await fs.rm(tempDir, { recursive: true, force: true });
				} catch {
					// Ignore cleanup errors
				}
			}

			this.addToHistory({
				timestamp: new Date(),
				collectionsProcessed: [],
				totalDocumentsProcessed: 0,
				success: false
			});
		}

		return result;
	}
}

// Export singleton instance
export const backupService = new BackupService();
