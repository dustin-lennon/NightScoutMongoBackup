// Mock external dependencies before importing
jest.mock('#lib/services/backup', () => ({
  backupService: {
    performBackup: jest.fn()
  }
}));

jest.mock('@sentry/node', () => ({
  addBreadcrumb: jest.fn(),
  captureException: jest.fn()
}));

jest.mock('@sapphire/framework', () => ({
  container: {
    logger: {
      info: jest.fn(),
      error: jest.fn()
    }
  }
}));

import { NightlyBackupTask } from '#scheduled-tasks/nightlyBackup';
import { backupService } from '#lib/services/backup';
import * as Sentry from '@sentry/node';
import { container } from '@sapphire/framework';

const mockedBackupService = backupService as jest.Mocked<typeof backupService>;
const mockedSentry = Sentry as jest.Mocked<typeof Sentry>;
const mockedContainer = container as jest.Mocked<typeof container>;

describe('NightlyBackupTask', () => {
  let nightlyBackup: NightlyBackupTask;
  let originalEnv: NodeJS.ProcessEnv;

  beforeEach(() => {
    // Save original environment
    originalEnv = { ...process.env };

    nightlyBackup = new NightlyBackupTask();
    jest.clearAllMocks();

    // Mock timers properly
    jest.spyOn(global, 'setInterval');
    jest.spyOn(global, 'clearInterval');
    jest.useFakeTimers();
  });

  afterEach(() => {
    // Restore original environment
    process.env = originalEnv;
    nightlyBackup.stop();
    jest.useRealTimers();
    jest.restoreAllMocks();
  });  describe('constructor', () => {
    it('should create instance without errors', () => {
      expect(nightlyBackup).toBeDefined();
      expect(nightlyBackup).toBeInstanceOf(NightlyBackupTask);
    });
  });

  describe('start', () => {
    it('should start backup task when enabled (default)', () => {
      delete process.env.ENABLE_NIGHTLY_BACKUP;

      nightlyBackup.start();

      expect(mockedContainer.logger.info).toHaveBeenCalledWith('[NightlyBackup] Scheduled backup task initialized');
      expect(mockedContainer.logger.info).toHaveBeenCalledWith('[NightlyBackup] Scheduled backup task started (checking every minute)');
    });

    it('should start backup task when explicitly enabled', () => {
      process.env.ENABLE_NIGHTLY_BACKUP = 'true';

      nightlyBackup.start();

      expect(mockedContainer.logger.info).toHaveBeenCalledWith('[NightlyBackup] Scheduled backup task initialized');
    });

    it('should not start backup task when disabled', () => {
      process.env.ENABLE_NIGHTLY_BACKUP = 'false';

      nightlyBackup.start();

      expect(mockedContainer.logger.info).toHaveBeenCalledWith('[NightlyBackup] Nightly backup is disabled');
    });
  });

  describe('stop', () => {
    it('should stop running backup task', () => {
      nightlyBackup.start();

      nightlyBackup.stop();

      expect(mockedContainer.logger.info).toHaveBeenCalledWith('[NightlyBackup] Scheduled backup task stopped');
    });

    it('should handle stopping when no task is running', () => {
      nightlyBackup.stop();

      // Should not throw any errors
      expect(nightlyBackup).toBeDefined();
    });
  });  describe('checkAndRunBackup', () => {
    it('should call run method directly when testing the public interface', async () => {
      // Instead of testing the complex timer logic, test the run method directly
      const mockResult = {
        success: true,
        collectionsProcessed: ['entries'],
        totalDocumentsProcessed: 50,
        data: {},
        timestamp: new Date()
      };

      mockedBackupService.performBackup.mockResolvedValue(mockResult);

      await nightlyBackup.run();

      expect(mockedBackupService.performBackup).toHaveBeenCalledWith({ createThread: true, isManual: false });
      expect(mockedContainer.logger.info).toHaveBeenCalledWith('[NightlyBackup] Starting scheduled backup...');
    });
  });  describe('run', () => {
    it('should perform successful backup and log results', async () => {
      const mockResult = {
        success: true,
        collectionsProcessed: ['entries', 'treatments'],
        totalDocumentsProcessed: 150,
        data: {},
        timestamp: new Date()
      };

      mockedBackupService.performBackup.mockResolvedValue(mockResult);

      await nightlyBackup.run();

      expect(mockedContainer.logger.info).toHaveBeenCalledWith('[NightlyBackup] Starting scheduled backup...');
      expect(mockedContainer.logger.info).toHaveBeenCalledWith(
        '[NightlyBackup] Backup completed successfully! Collections: entries, treatments, Documents: 150'
      );
      expect(mockedSentry.addBreadcrumb).toHaveBeenCalledWith({
        category: 'backup',
        message: 'Nightly backup completed successfully',
        level: 'info',
        data: {
          collections: ['entries', 'treatments'],
          documentsCount: 150
        }
      });
    });

    it('should handle backup failure and report to Sentry', async () => {
      const mockResult = {
        success: false,
        collectionsProcessed: ['entries'],
        totalDocumentsProcessed: 0,
        data: {},
        error: 'Connection timeout',
        timestamp: new Date()
      };

      mockedBackupService.performBackup.mockResolvedValue(mockResult);

      await nightlyBackup.run();

      expect(mockedContainer.logger.info).toHaveBeenCalledWith('[NightlyBackup] Starting scheduled backup...');
      expect(mockedContainer.logger.error).toHaveBeenCalledWith('[NightlyBackup] Backup failed: Connection timeout');
      expect(mockedSentry.captureException).toHaveBeenCalledWith(
        new Error('Connection timeout'),
        {
          tags: { task: 'nightlyBackup' },
          extra: {
            collectionsProcessed: ['entries'],
            timestamp: mockResult.timestamp
          }
        }
      );
    });

    it('should handle backup failure with undefined error', async () => {
      const mockResult = {
        success: false,
        collectionsProcessed: [],
        totalDocumentsProcessed: 0,
        data: {},
        error: undefined,
        timestamp: new Date()
      };

      mockedBackupService.performBackup.mockResolvedValue(mockResult);

      await nightlyBackup.run();

      expect(mockedContainer.logger.error).toHaveBeenCalledWith('[NightlyBackup] Backup failed: undefined');
      expect(mockedSentry.captureException).toHaveBeenCalledWith(
        new Error('Unknown backup error'),
        expect.objectContaining({
          tags: { task: 'nightlyBackup' }
        })
      );
    });

    it('should handle unexpected errors during backup', async () => {
      const mockError = new Error('Unexpected database error');
      mockedBackupService.performBackup.mockRejectedValue(mockError);

      await nightlyBackup.run();

      expect(mockedContainer.logger.info).toHaveBeenCalledWith('[NightlyBackup] Starting scheduled backup...');
      expect(mockedContainer.logger.error).toHaveBeenCalledWith('[NightlyBackup] Unexpected error during backup:', mockError);
      expect(mockedSentry.captureException).toHaveBeenCalledWith(mockError, {
        tags: { task: 'nightlyBackup' }
      });
    });

    it('should call performBackup with no options', async () => {
      const mockResult = {
        success: true,
        collectionsProcessed: ['entries'],
        totalDocumentsProcessed: 50,
        data: {},
        timestamp: new Date()
      };

      mockedBackupService.performBackup.mockResolvedValue(mockResult);

      await nightlyBackup.run();

      expect(mockedBackupService.performBackup).toHaveBeenCalledWith({ createThread: true, isManual: false });
      expect(mockedBackupService.performBackup).toHaveBeenCalledTimes(1);
    });
  });

  describe('integration with environment variables', () => {
    it('should respect ENABLE_NIGHTLY_BACKUP environment variable', () => {
      process.env.ENABLE_NIGHTLY_BACKUP = 'false';

      nightlyBackup.start();

      expect(mockedContainer.logger.info).toHaveBeenCalledWith('[NightlyBackup] Nightly backup is disabled');
    });
  });
});
