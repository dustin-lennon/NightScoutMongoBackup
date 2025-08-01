
import { jest } from '@jest/globals';
import { backupService } from '#lib/services/backup-simple';

// Mock the container
jest.mock('@sapphire/framework', () => ({
	container: {
		client: {
			emit: jest.fn()
		},
		logger: {
			info: jest.fn(),
			error: jest.fn(),
			warn: jest.fn(),
			debug: jest.fn()
		}
	}
}));

// Mock services
jest.mock('#lib/services/mongo', () => ({
	mongoService: {
		getCollection: jest.fn()
	}
}));

jest.mock('#lib/services/discordThread', () => ({
	discordThreadService: {
		createBackupThread: jest.fn(),
		sendBackupErrorMessage: jest.fn(),
		sendBackupStartMessage: jest.fn(),
		sendBackupProgressMessage: jest.fn(),
		sendBackupCompleteMessage: jest.fn()
	}
}));

// Import mocked services after mocking
import { mongoService } from '#lib/services/mongo';
import { discordThreadService } from '#lib/services/discordThread';

const mockMongoService = mongoService as jest.Mocked<typeof mongoService>;
const mockDiscordThreadService = discordThreadService as jest.Mocked<typeof discordThreadService>;

describe('Backup Simple Service', () => {
	beforeEach(() => {
		jest.clearAllMocks();
		// Reset module registry to ensure fresh imports
		jest.resetModules();

		// Setup default successful mocks for Discord thread service
		mockDiscordThreadService.sendBackupStartMessage.mockResolvedValue({ success: true });
		mockDiscordThreadService.sendBackupProgressMessage.mockResolvedValue({ success: true });
		mockDiscordThreadService.sendBackupCompleteMessage.mockResolvedValue({ success: true });
		mockDiscordThreadService.sendBackupErrorMessage.mockResolvedValue({ success: true });
	});

	describe('performBackup', () => {
		it('should successfully backup specified collections', async () => {
			// Mock collection data
			const mockEntries = [
				{ _id: '1', sgv: 120, date: new Date() },
				{ _id: '2', sgv: 130, date: new Date() }
			];

			// Mock mongo service to return collection with data
			mockMongoService.getCollection.mockResolvedValue({
				find: jest.fn().mockReturnValue({
					// @ts-ignore - Jest mock typing issue
					toArray: jest.fn().mockResolvedValue(mockEntries)
				})
			} as any);

			mockDiscordThreadService.createBackupThread.mockResolvedValue({
				success: true,
				threadId: 'thread-123'
			});

			// Perform backup
			const result = await backupService.performBackup({
				collections: ['entries'],
				createThread: true,
				isManual: true
			});

			// Assertions
			expect(result.success).toBe(true);
			expect(result.collectionsProcessed).toEqual(['entries']);
			expect(result.totalDocumentsProcessed).toBe(2);
			expect(result.threadId).toBe('thread-123');
			expect(result.error).toBeUndefined();
			expect(mockDiscordThreadService.createBackupThread).toHaveBeenCalledWith(
				expect.stringMatching(/^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$/)
			);
		});

		it('should backup multiple collections', async () => {
			// Mock different data for different collections
			mockMongoService.getCollection.mockImplementation((collectionName) => {
				if (collectionName === 'entries') {
					return Promise.resolve({
						find: jest.fn().mockReturnValue({
							// @ts-ignore
							toArray: jest.fn().mockResolvedValue([
								{ _id: '1', sgv: 120 },
								{ _id: '2', sgv: 130 }
							])
						})
					} as any);
				}
				if (collectionName === 'treatments') {
					return Promise.resolve({
						find: jest.fn().mockReturnValue({
							// @ts-ignore
							toArray: jest.fn().mockResolvedValue([
								{ _id: '1', eventType: 'BG Check' }
							])
						})
					} as any);
				}
				return Promise.resolve({
					find: jest.fn().mockReturnValue({
						// @ts-ignore
						toArray: jest.fn().mockResolvedValue([])
					})
				} as any);
			});

			// Perform backup without thread creation
			const result = await backupService.performBackup({
				collections: ['entries', 'treatments'],
				createThread: false,
				isManual: true
			});

			// Assertions
			expect(result.success).toBe(true);
			expect(result.collectionsProcessed).toEqual(['entries', 'treatments']);
			expect(result.totalDocumentsProcessed).toBe(3);
			expect(result.threadId).toBeUndefined();
		});

		it('should handle empty collections gracefully', async () => {
			// Mock empty collection
			mockMongoService.getCollection.mockResolvedValue({
				find: jest.fn().mockReturnValue({
					// @ts-ignore
					toArray: jest.fn().mockResolvedValue([])
				})
			} as any);

			// Perform backup
			const result = await backupService.performBackup({
				collections: ['empty_collection'],
				createThread: false,
				isManual: true
			});

			// Assertions
			expect(result.success).toBe(true);
			expect(result.collectionsProcessed).toEqual(['empty_collection']);
			expect(result.totalDocumentsProcessed).toBe(0);
		});

		it('should handle collection access errors and continue with other collections', async () => {
			// Mock mixed success/failure for different collections
			mockMongoService.getCollection.mockImplementation((collectionName) => {
				if (collectionName === 'failing_collection') {
					return Promise.reject(new Error('Collection access failed'));
				}
				if (collectionName === 'working_collection') {
					return Promise.resolve({
						find: jest.fn().mockReturnValue({
							// @ts-ignore
							toArray: jest.fn().mockResolvedValue([
								{ _id: '1', data: 'test' }
							])
						})
					} as any);
				}
				return Promise.resolve({
					find: jest.fn().mockReturnValue({
						// @ts-ignore
						toArray: jest.fn().mockResolvedValue([])
					})
				} as any);
			});

			// Perform backup
			const result = await backupService.performBackup({
				collections: ['failing_collection', 'working_collection'],
				createThread: false,
				isManual: true
			});

			// Should succeed with partial results
			expect(result.success).toBe(true);
			expect(result.collectionsProcessed).toEqual(['working_collection']);
			expect(result.totalDocumentsProcessed).toBe(1);
		});

		it('should handle query errors and continue with other collections', async () => {
			// Mock collection that returns but fails on query
			mockMongoService.getCollection.mockImplementation((collectionName) => {
				if (collectionName === 'query_failing') {
					return Promise.resolve({
						find: jest.fn().mockReturnValue({
							// @ts-ignore
							toArray: jest.fn().mockRejectedValue(new Error('Query failed'))
						})
					} as any);
				}
				if (collectionName === 'query_working') {
					return Promise.resolve({
						find: jest.fn().mockReturnValue({
							// @ts-ignore
							toArray: jest.fn().mockResolvedValue([
								{ _id: '1', data: 'test' }
							])
						})
					} as any);
				}
				return Promise.resolve({
					find: jest.fn().mockReturnValue({
						// @ts-ignore
						toArray: jest.fn().mockResolvedValue([])
					})
				} as any);
			});

			// Perform backup
			const result = await backupService.performBackup({
				collections: ['query_failing', 'query_working'],
				createThread: false,
				isManual: true
			});

			// Should succeed with partial results
			expect(result.success).toBe(true);
			expect(result.collectionsProcessed).toEqual(['query_working']);
			expect(result.totalDocumentsProcessed).toBe(1);
		});

		it('should create thread when requested', async () => {
			// Mock minimal collection
			mockMongoService.getCollection.mockResolvedValue({
				find: jest.fn().mockReturnValue({
					// @ts-ignore
					toArray: jest.fn().mockResolvedValue([])
				})
			} as any);

			mockDiscordThreadService.createBackupThread.mockResolvedValue({
				success: true,
				threadId: 'thread-456'
			});

			// Perform backup with thread creation
			const result = await backupService.performBackup({
				collections: ['test'],
				createThread: true,
				isManual: false
			});

			// Assertions
			expect(result.success).toBe(true);
			expect(result.threadId).toBe('thread-456');
			expect(mockDiscordThreadService.createBackupThread).toHaveBeenCalledWith(
				expect.stringMatching(/^\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2}$/)
			);
		});

		it('should handle thread creation failure gracefully', async () => {
			// Mock collection
			mockMongoService.getCollection.mockResolvedValue({
				find: jest.fn().mockReturnValue({
					// @ts-ignore
					toArray: jest.fn().mockResolvedValue([])
				})
			} as any);

			// Mock thread creation failure
			mockDiscordThreadService.createBackupThread.mockResolvedValue({
				success: false,
				error: 'Thread creation failed'
			});

			// Perform backup
			const result = await backupService.performBackup({
				collections: ['test'],
				createThread: true,
				isManual: true
			});

			// Should still succeed with backup, just no thread
			expect(result.success).toBe(true);
			expect(result.threadId).toBeUndefined();
			expect(result.collectionsProcessed).toEqual(['test']);
		});

		it('should use default collections when none specified', async () => {
			// Mock empty collections for default collection names
			const defaultCollections = ['entries', 'devicestatus', 'treatments', 'profile'];

			mockMongoService.getCollection.mockResolvedValue({
				find: jest.fn().mockReturnValue({
					// @ts-ignore
					toArray: jest.fn().mockResolvedValue([])
				})
			} as any);

			// Perform backup without specifying collections
			const result = await backupService.performBackup({
				createThread: false,
				isManual: true
			});

			// Should process default collections
			expect(result.success).toBe(true);
			expect(result.collectionsProcessed).toEqual(defaultCollections);
			expect(mockMongoService.getCollection).toHaveBeenCalledTimes(defaultCollections.length);

			// Verify each default collection was called
			defaultCollections.forEach(collectionName => {
				expect(mockMongoService.getCollection).toHaveBeenCalledWith(collectionName);
			});
		});

		it('should fail completely when no collections are successfully processed', async () => {
			// Mock all collections to fail
			mockMongoService.getCollection.mockRejectedValue(new Error('Database connection failed'));

			// Perform backup
			const result = await backupService.performBackup({
				collections: ['entries'],
				createThread: false,
				isManual: true
			});

			// Should fail completely
			expect(result.success).toBe(false);
			expect(result.collectionsProcessed).toEqual([]);
			expect(result.totalDocumentsProcessed).toBe(0);
			expect(result.error).toBe('No collections were successfully backed up');
		});

		it('should handle thread creation failure and send error to thread', async () => {
			// Mock collection to fail
			mockMongoService.getCollection.mockRejectedValue(new Error('Connection timeout'));

			// Mock successful thread creation
			mockDiscordThreadService.createBackupThread.mockResolvedValue({
				success: true,
				threadId: 'thread-error-test'
			});

			// Perform backup
			const result = await backupService.performBackup({
				collections: ['entries'],
				createThread: true,
				isManual: true
			});

			// Should fail and send error to thread
			expect(result.success).toBe(false);
			expect(result.error).toBe('No collections were successfully backed up');
			expect(mockDiscordThreadService.sendBackupErrorMessage).toHaveBeenCalledWith(
				'thread-error-test',
				'No collections were successfully backed up'
			);
		});

		it('should track backup history for both successful and failed backups', async () => {
			// Simply test that history tracking works (we know there may be previous entries)
			const startHistoryLength = backupService.getBackupHistory().length;

			// Test successful backup history tracking
			mockMongoService.getCollection.mockResolvedValue({
				find: jest.fn().mockReturnValue({
					// @ts-ignore
					toArray: jest.fn().mockResolvedValue([{ _id: '1', data: 'test' }])
				})
			} as any);

			await backupService.performBackup({
				collections: ['entries'],
				createThread: false,
				isManual: true
			});

			// Now test failed backup history tracking
			mockMongoService.getCollection.mockRejectedValue(new Error('Database error'));

			await backupService.performBackup({
				collections: ['entries'],
				createThread: false,
				isManual: true
			});

			// Check history has increased (the history is capped at 10, so it may be less than +2)
			const history = backupService.getBackupHistory();
			expect(history.length).toBeGreaterThanOrEqual(Math.min(10, startHistoryLength + 2));

			// Check the last two entries show success/failure pattern
			const lastTwo = history.slice(-2);
			expect(lastTwo[0].success).toBe(true);
			expect(lastTwo[1].success).toBe(false);
		});		it('should limit backup history to 10 records', async () => {
			// Mock successful backup
			mockMongoService.getCollection.mockResolvedValue({
				find: jest.fn().mockReturnValue({
					// @ts-ignore
					toArray: jest.fn().mockResolvedValue([])
				})
			} as any);

			// Perform 12 backups to test history limit
			for (let i = 0; i < 12; i++) {
				await backupService.performBackup({
					collections: ['entries'],
					createThread: false,
					isManual: true
				});
			}

			// Should only keep last 10
			const history = backupService.getBackupHistory();
			expect(history).toHaveLength(10);
		});
	});

	describe('getBackupHistory', () => {
		it('should return a copy of backup history', () => {
			const history1 = backupService.getBackupHistory();
			const history2 = backupService.getBackupHistory();

			// Should be different objects (copies)
			expect(history1).not.toBe(history2);
			expect(history1).toEqual(history2);
		});
	});
});
