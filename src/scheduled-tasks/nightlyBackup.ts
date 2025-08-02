import { backupService } from '#lib/services/backup';
import { envParseString } from '@skyra/env-utilities';
import * as Sentry from '@sentry/node';
import { container } from '@sapphire/framework';

export class NightlyBackupTask {
	private intervalId: NodeJS.Timeout | null = null;
	private readonly checkInterval = 60000; // Check every minute

	constructor() {
		// Constructor now only sets up the class without accessing container
	}

	public start(): void {
		const enabled = envParseString('ENABLE_NIGHTLY_BACKUP', 'true') !== 'false'; // Enabled by default

		if (!enabled) {
			container.logger.info('[NightlyBackup] Nightly backup is disabled');
			return;
		}

		container.logger.info('[NightlyBackup] Scheduled backup task initialized');

		// Schedule backup check every minute
		this.intervalId = setInterval(() => {
			this.checkAndRunBackup();
		}, this.checkInterval);

		container.logger.info('[NightlyBackup] Scheduled backup task started (checking every minute)');
	}

	public stop(): void {
		if (this.intervalId) {
			clearInterval(this.intervalId);
			this.intervalId = null;
			container.logger.info('[NightlyBackup] Scheduled backup task stopped');
		}
	}

	private checkAndRunBackup(): void {
		const now = new Date();
		const targetHour = parseInt(envParseString('BACKUP_HOUR', '2'), 10); // Default: 2 AM
		const targetMinute = parseInt(envParseString('BACKUP_MINUTE', '0'), 10); // Default: 0 minutes

		// Check if it's the right time to run backup (within the target minute)
		if (now.getHours() === targetHour && now.getMinutes() === targetMinute) {
			this.run();
		}
	}

	public async run(): Promise<void> {
		container.logger.info('[NightlyBackup] Starting scheduled backup...');

		try {
			const result = await backupService.performBackup({
				createThread: true,
				isManual: false
			});

			if (result.success) {
				container.logger.info(
					`[NightlyBackup] Backup completed successfully! ` +
					`Collections: ${result.collectionsProcessed.join(', ')}, ` +
					`Documents: ${result.totalDocumentsProcessed}`
				);

				// Add Sentry breadcrumb for successful backup
				Sentry.addBreadcrumb({
					category: 'backup',
					message: 'Nightly backup completed successfully',
					level: 'info',
					data: {
						collections: result.collectionsProcessed,
						documentsCount: result.totalDocumentsProcessed
					}
				});
			} else {
				container.logger.error(`[NightlyBackup] Backup failed: ${result.error}`);

				// Report backup failure to Sentry
				Sentry.captureException(new Error(result.error || 'Unknown backup error'), {
					tags: {
						task: 'nightlyBackup'
					},
					extra: {
						collectionsProcessed: result.collectionsProcessed,
						timestamp: result.timestamp
					}
				});
			}
		} catch (error) {
			container.logger.error('[NightlyBackup] Unexpected error during backup:', error);

			// Report unexpected errors to Sentry
			Sentry.captureException(error, {
				tags: {
					task: 'nightlyBackup'
				}
			});
		}
	}
}
