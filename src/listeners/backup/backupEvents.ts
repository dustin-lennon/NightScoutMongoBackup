import { Listener } from '@sapphire/framework';
import type { BackupEventData } from '../../lib/services/backup';

export class BackupCompletedListener extends Listener {
	public constructor(context: Listener.LoaderContext, options: Listener.Options) {
		super(context, {
			...options,
			event: 'backupCompleted'
		});
	}

	public run(data: BackupEventData) {
		this.container.logger.info(`Backup completed successfully: ${data.filename}`);

		// Additional post-backup processing can be added here
		// e.g., cleanup old backups, send notifications, etc.
	}
}

export class BackupFailedListener extends Listener {
	public constructor(context: Listener.LoaderContext, options: Listener.Options) {
		super(context, {
			...options,
			event: 'backupFailed'
		});
	}

	public run(data: { error: Error; operation: string }) {
		this.container.logger.error(`Backup failed during ${data.operation}:`, data.error);

		// Additional error handling can be added here
		// e.g., alert administrators, retry logic, etc.
	}
}
