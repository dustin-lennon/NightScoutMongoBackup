import { BackupCompletedListener, BackupFailedListener } from '#listeners/backup/backupEvents';
import type { BackupEventData } from '#lib/services/backup';

describe('Backup Event Listeners', () => {
	let completedListener: BackupCompletedListener;
	let failedListener: BackupFailedListener;
	const mockLogger = {
		info: jest.fn(),
		error: jest.fn()
	};

	beforeEach(() => {
		jest.clearAllMocks();

		completedListener = new BackupCompletedListener({ name: 'backupCompleted', path: '' } as any, {});
		failedListener = new BackupFailedListener({ name: 'backupFailed', path: '' } as any, {});

		// Mock the container property
		Object.defineProperty(completedListener, 'container', {
			value: { logger: mockLogger },
			writable: false
		});
		Object.defineProperty(failedListener, 'container', {
			value: { logger: mockLogger },
			writable: false
		});
	});

	describe('BackupCompletedListener', () => {
		it('should log backup completion', () => {
			const eventData: BackupEventData = {
				filename: 'backup-2025-07-30.tar.gz',
				timestamp: new Date(),
				success: true,
				s3Url: 'https://s3.example.com/backup.tar.gz',
				collections: ['entries', 'treatments'],
				size: 1024000
			};

			completedListener.run(eventData);

			expect(mockLogger.info).toHaveBeenCalledWith('Backup completed successfully: backup-2025-07-30.tar.gz');
		});
	});

	describe('BackupFailedListener', () => {
		it('should log backup failure', () => {
			const error = new Error('Backup failed');
			const eventData = {
				error,
				operation: 'compression'
			};

			failedListener.run(eventData);

			expect(mockLogger.error).toHaveBeenCalledWith('Backup failed during compression:', error);
		});
	});
});
