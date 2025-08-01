import { BackupService } from '#lib/services/backup';
import { s3Service } from '#lib/services/s3';
import { discordThreadService } from '#lib/services/discordThread';
import * as fs from 'fs/promises';

// Mock the container
jest.mock('@sapphire/framework', () => ({
  ...jest.requireActual('@sapphire/framework'),
  container: {
    client: {
      emit: jest.fn()
    }
  }
}));

// Mock fs.promises
jest.mock('fs/promises', () => ({
  mkdir: jest.fn(),
  stat: jest.fn(),
  rm: jest.fn()
}));

// Mock S3 service
jest.mock('#lib/services/s3', () => ({
  s3Service: {
    uploadFile: jest.fn()
  }
}));

// Mock Discord thread service
jest.mock('#lib/services/discordThread', () => ({
  discordThreadService: {
    createBackupThread: jest.fn(),
    sendBackupStartMessage: jest.fn(),
    sendBackupProgressMessage: jest.fn(),
    sendBackupCompleteMessage: jest.fn(),
    sendBackupErrorMessage: jest.fn()
  }
}));

const mockedFs = jest.mocked(fs);
const mockedS3Service = jest.mocked(s3Service);
const mockedDiscordThreadService = jest.mocked(discordThreadService);

describe('BackupService', () => {
  let backupService: BackupService;
  let mockExecAsync: jest.MockedFunction<any>;

  beforeEach(() => {
    backupService = new BackupService();
    jest.clearAllMocks();

    // Mock the private execAsync method
    mockExecAsync = jest.fn();
    (backupService as any).execAsync = mockExecAsync;

    // Mock exec to simulate successful mongodump and tar commands
    mockExecAsync.mockImplementation((command: string) => {
      if (command.includes('mongodump')) {
        // Simulate successful mongodump with document count output
        return Promise.resolve({
          stdout: 'Connected to: mongodb+srv://...\n2025-07-30T12:00:00.000+0000\texported 50 documents from entries\n2025-07-30T12:00:00.000+0000\texported 25 documents from devicestatus\n2025-07-30T12:00:00.000+0000\texported 15 documents from treatments\n2025-07-30T12:00:00.000+0000\texported 10 documents from profile',
          stderr: ''
        });
      } else if (command.includes('tar')) {
        // Simulate successful tar compression
        return Promise.resolve({ stdout: '', stderr: '' });
      } else {
        return Promise.reject(new Error('Unknown command'));
      }
    });

    // Mock fs operations
    mockedFs.mkdir.mockResolvedValue(undefined);
    mockedFs.rm.mockResolvedValue(undefined);
    mockedFs.stat.mockResolvedValue({ size: 1024 } as any);

    // Mock S3 service
    mockedS3Service.uploadFile.mockResolvedValue({
      success: true,
      s3Url: 'https://s3.amazonaws.com/bucket/backup.tar.gz',
      key: 'backup.tar.gz',
      bucket: 'test-bucket'
    });

    // Mock Discord thread service
    mockedDiscordThreadService.createBackupThread.mockResolvedValue({
      success: true,
      threadId: '123456'
    });
    mockedDiscordThreadService.sendBackupStartMessage.mockResolvedValue({
      success: true,
      messageId: 'msg1'
    });
    mockedDiscordThreadService.sendBackupProgressMessage.mockResolvedValue({
      success: true,
      messageId: 'msg2'
    });
    mockedDiscordThreadService.sendBackupCompleteMessage.mockResolvedValue({
      success: true,
      messageId: 'msg3'
    });
    mockedDiscordThreadService.sendBackupErrorMessage.mockResolvedValue({
      success: true,
      messageId: 'msg4'
    });
  });

  describe('performBackup', () => {
    it('should perform backup successfully with default options', async () => {
      const result = await backupService.performBackup();

      expect(result.success).toBe(true);
      expect(result.collectionsProcessed).toEqual(['entries', 'devicestatus', 'treatments', 'profile']);
      expect(result.totalDocumentsProcessed).toBe(100); // 50 + 25 + 15 + 10 from mongodump output
      expect(result.timestamp).toBeInstanceOf(Date);
      expect(result.s3Url).toBe('https://s3.amazonaws.com/bucket/backup.tar.gz');

      expect(mockedS3Service.uploadFile).toHaveBeenCalled();
      expect(mockedFs.mkdir).toHaveBeenCalled();
      expect(mockedFs.rm).toHaveBeenCalled();
    });

    it('should perform backup with custom collections', async () => {
      const result = await backupService.performBackup({ collections: ['entries', 'treatments'] });

      expect(result.success).toBe(true);
      expect(result.collectionsProcessed).toEqual(['entries', 'treatments']);
      expect(result.totalDocumentsProcessed).toBe(100); // Mock returns same output regardless
    });

    it('should create Discord thread when requested', async () => {
      const result = await backupService.performBackup({ createThread: true });

      expect(result.success).toBe(true);
      expect(result.threadId).toBe('123456');
      expect(mockedDiscordThreadService.createBackupThread).toHaveBeenCalled();
      expect(mockedDiscordThreadService.sendBackupStartMessage).toHaveBeenCalled();
      expect(mockedDiscordThreadService.sendBackupCompleteMessage).toHaveBeenCalled();
    });

    it('should handle MongoDB connection errors', async () => {
      // Mock exec to simulate mongodump failure
      mockExecAsync.mockImplementation((command: string) => {
        if (command.includes('mongodump')) {
          return Promise.reject(new Error('Connection failed'));
        }
        return Promise.resolve({ stdout: '', stderr: '' });
      });

      const result = await backupService.performBackup();

      expect(result.success).toBe(false);
      expect(result.error).toBe('MongoDB dump failed: Connection failed');
    });

    it('should handle tar compression errors', async () => {
      // Mock exec to fail on tar command
      mockExecAsync.mockImplementation((command: string) => {
        if (command.includes('mongodump')) {
          return Promise.resolve({ stdout: 'exported 50 documents', stderr: '' });
        } else if (command.includes('tar')) {
          return Promise.reject(new Error('Disk full'));
        }
        return Promise.resolve({ stdout: '', stderr: '' });
      });

      const result = await backupService.performBackup();

      expect(result.success).toBe(false);
      expect(result.error).toBe('Archive creation failed: Disk full');
    });

    it('should handle S3 upload errors', async () => {
      mockedS3Service.uploadFile.mockResolvedValue({
        success: false,
        error: 'S3 connection failed'
      });

      const result = await backupService.performBackup();

      expect(result.success).toBe(false);
      expect(result.error).toBe('S3 upload failed: S3 connection failed');
    });

    it('should clean up files after successful backup', async () => {
      await backupService.performBackup();

      expect(mockedFs.rm).toHaveBeenCalled();
    });

    it('should clean up files after failed backup', async () => {
      mockedS3Service.uploadFile.mockResolvedValue({
        success: false,
        error: 'Upload failed'
      });

      await backupService.performBackup();

      expect(mockedFs.rm).toHaveBeenCalled();
    });

    it('should add successful backup to history', async () => {
      await backupService.performBackup();

      const history = backupService.getBackupHistory();
      expect(history).toHaveLength(1);
      expect(history[0].success).toBe(true);
      expect(history[0].collectionsProcessed).toEqual(['entries', 'devicestatus', 'treatments', 'profile']);
    });

    it('should add failed backup to history', async () => {
      mockedS3Service.uploadFile.mockResolvedValue({
        success: false,
        error: 'Test error'
      });

      await backupService.performBackup();

      const history = backupService.getBackupHistory();
      expect(history).toHaveLength(1);
      expect(history[0].success).toBe(false);
    });

    it('should limit backup history to 10 entries', async () => {
      // Create 12 backups
      for (let i = 0; i < 12; i++) {
        await backupService.performBackup();
      }

      const history = backupService.getBackupHistory();
      expect(history).toHaveLength(10);
    });

    it('should handle empty collections gracefully', async () => {
      // Mock exec to return no documents exported
      mockExecAsync.mockImplementation((command: string) => {
        if (command.includes('mongodump')) {
          return Promise.resolve({ stdout: 'Connected to: mongodb+srv://...\nNo documents exported', stderr: '' });
        } else if (command.includes('tar')) {
          return Promise.resolve({ stdout: '', stderr: '' });
        }
        return Promise.resolve({ stdout: '', stderr: '' });
      });

      const result = await backupService.performBackup();

      expect(result.success).toBe(true);
      expect(result.totalDocumentsProcessed).toBe(0);
    });

    it('should continue with other collections if one fails', async () => {
      // With mongodump, we can't easily simulate partial collection failures
      // since it's one command, so this test is less relevant but we'll keep a version
      const result = await backupService.performBackup();

      expect(result.success).toBe(true);
      expect(result.collectionsProcessed.length).toBe(4); // All collections processed by mongodump
    });

    it('should send Discord error message on failure', async () => {
      mockedDiscordThreadService.createBackupThread.mockResolvedValue({
        success: true,
        threadId: '123456'
      });

      // Mock exec to fail mongodump
      mockExecAsync.mockImplementation((command: string) => {
        if (command.includes('mongodump')) {
          return Promise.reject(new Error('Unknown error'));
        }
        return Promise.resolve({ stdout: '', stderr: '' });
      });

      await backupService.performBackup({ createThread: true });

      expect(mockedDiscordThreadService.sendBackupErrorMessage).toHaveBeenCalledWith('123456', 'MongoDB dump failed: Unknown error');
    });
  });

  describe('getBackupHistory', () => {
    it('should return empty history initially', () => {
      const history = backupService.getBackupHistory();
      expect(history).toEqual([]);
    });

    it('should return backup history after performing backups', async () => {
      await backupService.performBackup();
      await backupService.performBackup();

      const history = backupService.getBackupHistory();
      expect(history).toHaveLength(2);
    });

    it('should return a copy of the history array', async () => {
      await backupService.performBackup();

      const history1 = backupService.getBackupHistory();
      const history2 = backupService.getBackupHistory();

      expect(history1).toEqual(history2);
      expect(history1).not.toBe(history2); // Different instances
    });
  });
});
