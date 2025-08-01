import { mongoService } from '#lib/services/mongo';
import { discordThreadService } from '#lib/services/discordThread';
import { Document } from 'mongodb';
import { container } from '@sapphire/framework';

export interface BackupOptions {
	collections?: string[];
	createThread?: boolean;
	isManual?: boolean;
}

export interface BackupResult {
	success: boolean;
	collectionsProcessed: string[];
	totalDocumentsProcessed: number;
	data?: Record<string, Document[]>;
	error?: string;
	timestamp: Date;
	threadId?: string;
}

export interface BackupStats {
	timestamp: Date;
	collectionsProcessed: string[];
	totalDocumentsProcessed: number;
	success: boolean;
}

export interface BackupEventData {
	timestamp: Date;
	success: boolean;
	collections: string[];
	totalDocuments: number;
}

export class BackupService {
	private readonly defaultCollections = ['entries', 'devicestatus', 'treatments', 'profile'];
	private backupHistory: BackupStats[] = [];

	async performBackup(options: BackupOptions = {}): Promise<BackupResult> {
		const startTime = new Date();
		const backupId = startTime.toISOString().slice(0, 19).replace(/[T:]/g, '-');

		const result: BackupResult = {
			success: false,
			collectionsProcessed: [],
			totalDocumentsProcessed: 0,
			timestamp: startTime,
			data: {}
		};

		let threadId: string | undefined;

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

			// Step 2: Process each collection
			for (const collectionName of collectionsToBackup) {
				if (threadId) {
					await discordThreadService.sendBackupProgressMessage(
						threadId,
						`Processing ${collectionName}`,
						`Backing up collection: ${collectionName}...`
					);
				}

				try {
					const collection = await mongoService.getCollection(collectionName);
					const documents = await collection.find({}).toArray();

					result.data![collectionName] = documents;
					result.collectionsProcessed.push(collectionName);
					result.totalDocumentsProcessed += documents.length;

					container.logger.info(`[Backup] Collection ${collectionName}: ${documents.length} documents`);

				} catch (collectionError) {
					const errorMessage = collectionError instanceof Error ? collectionError.message : 'Unknown error';
					container.logger.warn(`[Backup] Failed to backup collection ${collectionName}: ${errorMessage}`);

					if (threadId) {
						await discordThreadService.sendBackupProgressMessage(
							threadId,
							`Warning: ${collectionName}`,
							`Failed to backup collection: ${errorMessage}`
						);
					}
					// Continue with other collections
				}
			}

			// Step 3: Mark as successful if we processed at least one collection
			if (result.collectionsProcessed.length > 0) {
				result.success = true;
				result.timestamp = new Date();

				if (threadId) {
					const duration = (result.timestamp.getTime() - startTime.getTime()) / 1000;

					await discordThreadService.sendBackupCompleteMessage(threadId, {
						collectionsProcessed: result.collectionsProcessed,
						totalDocuments: result.totalDocumentsProcessed,
						originalSize: undefined,
						compressedSize: undefined,
						compressionRatio: undefined,
						s3Url: undefined,
						duration
					});
				}

				// Add to history for tracking
				this.backupHistory.push({
					timestamp: result.timestamp,
					collectionsProcessed: [...result.collectionsProcessed],
					totalDocumentsProcessed: result.totalDocumentsProcessed,
					success: true
				});

				// Keep only last 10 backup records
				if (this.backupHistory.length > 10) {
					this.backupHistory = this.backupHistory.slice(-10);
				}

				// Emit backup completed event
				container.client.emit('backupCompleted', {
					timestamp: result.timestamp,
					success: true,
					collections: result.collectionsProcessed,
					totalDocuments: result.totalDocumentsProcessed
				} as BackupEventData);

			} else {
				throw new Error('No collections were successfully backed up');
			}

		} catch (error) {
			result.error = error instanceof Error ? error.message : 'Unknown error occurred';
			result.success = false;

			// Emit backup failed event
			container.client.emit('backupFailed', {
				error: error instanceof Error ? error : new Error('Unknown error occurred'),
				operation: 'backup'
			});

			// Send error message to thread if available
			if (threadId) {
				await discordThreadService.sendBackupErrorMessage(threadId, result.error);
			}

			this.backupHistory.push({
				timestamp: new Date(),
				collectionsProcessed: [...result.collectionsProcessed],
				totalDocumentsProcessed: result.totalDocumentsProcessed,
				success: false
			});
		}

		return result;
	}

	getBackupHistory(): BackupStats[] {
		return [...this.backupHistory];
	}
}

// Export singleton instance
export const backupService = new BackupService();
