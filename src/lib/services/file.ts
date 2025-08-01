import * as fs from 'fs/promises';
import * as path from 'path';
import { Document } from 'mongodb';
import { container } from '@sapphire/framework';

export interface FileOperationResult {
	success: boolean;
	filePath?: string;
	error?: string;
}

export class FileService {
	private readonly backupDir = path.join(process.cwd(), 'backups');

	async ensureBackupDirectory(): Promise<void> {
		try {
			await fs.access(this.backupDir);
		} catch {
			// Directory doesn't exist, create it with 775 permissions
			await fs.mkdir(this.backupDir, { mode: 0o775, recursive: true });
		}
	}

	async writeBackupData(
		data: Record<string, Document[]>,
		timestamp: Date
	): Promise<FileOperationResult> {
		try {
			await this.ensureBackupDirectory();

			const dateStr = timestamp.toISOString().replace(/[:.]/g, '-');
			const fileName = `nightscout-backup-${dateStr}.json`;
			const filePath = path.join(this.backupDir, fileName);

			// Write the backup data as JSON
			const backupContent = {
				timestamp: timestamp.toISOString(),
				collections: data,
				metadata: {
					totalCollections: Object.keys(data).length,
					totalDocuments: Object.values(data).reduce((sum, docs) => sum + docs.length, 0)
				}
			};

			await fs.writeFile(filePath, JSON.stringify(backupContent, null, 2), { mode: 0o664 });

			return {
				success: true,
				filePath
			};
		} catch (error) {
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Unknown file error'
			};
		}
	}

	async deleteFile(filePath: string): Promise<void> {
		try {
			await fs.unlink(filePath);
		} catch (error) {
			// Ignore errors when cleaning up
			container.logger.error(`Failed to delete file ${filePath}:`, error);
		}
	}

	async deleteDirectory(dirPath: string): Promise<void> {
		try {
			await fs.rm(dirPath, { recursive: true, force: true });
		} catch (error) {
			// Ignore errors when cleaning up
			container.logger.error(`Failed to delete directory ${dirPath}:`, error);
		}
	}

	getBackupDirectory(): string {
		return this.backupDir;
	}
}

export const fileService = new FileService();
