import { mongoService } from '#lib/services/mongo';
import { discordThreadService } from '#lib/services/discordThread';
import { container } from '@sapphire/framework';
import {
	BaseBackupService,
	BackupOptions,
	BackupResult,
	BackupEventData
} from '#lib/services/backup-base';

export class BackupService extends BaseBackupService {

	override async performBackup(options: BackupOptions = {}): Promise<BackupResult> {
		const startTime = new Date();
		const backupId = this.generateBackupId();

		const result: BackupResult = this.createInitialResult(startTime);

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
				this.addToHistory({
					timestamp: result.timestamp,
					collectionsProcessed: [...result.collectionsProcessed],
					totalDocumentsProcessed: result.totalDocumentsProcessed,
					success: true
				});

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

			this.addToHistory({
				timestamp: new Date(),
				collectionsProcessed: [...result.collectionsProcessed],
				totalDocumentsProcessed: result.totalDocumentsProcessed,
				success: false
			});
		}

		return result;
	}
}

// Export singleton instance
export const backupService = new BackupService();
