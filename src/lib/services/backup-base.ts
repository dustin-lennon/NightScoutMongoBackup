import { Document } from 'mongodb';

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
	backupPath?: string;
	compressedPath?: string;
	s3Url?: string;
	threadId?: string;
}

export interface BackupStats {
	timestamp: Date;
	collectionsProcessed: string[];
	totalDocumentsProcessed: number;
	success: boolean;
	s3Url?: string;
	size?: number;
}

export interface BackupEventData {
	filename?: string;
	timestamp: Date;
	success: boolean;
	s3Url?: string;
	collections: string[];
	size?: number;
	totalDocuments?: number;
}

export abstract class BaseBackupService {
	protected readonly defaultCollections = ['entries', 'devicestatus', 'treatments', 'profile'];
	protected backupHistory: BackupStats[] = [];

	protected addToHistory(stats: BackupStats): void {
		this.backupHistory.push(stats);

		// Keep only last 10 backup records
		if (this.backupHistory.length > 10) {
			this.backupHistory = this.backupHistory.slice(-10);
		}
	}

	getBackupHistory(): BackupStats[] {
		return [...this.backupHistory];
	}

	protected generateBackupId(): string {
		return new Date().toISOString().slice(0, 19).replace(/[T:]/g, '-');
	}

	protected createInitialResult(timestamp: Date): BackupResult {
		return {
			success: false,
			collectionsProcessed: [],
			totalDocumentsProcessed: 0,
			timestamp,
			data: {}
		};
	}

	abstract performBackup(options?: BackupOptions): Promise<BackupResult>;
}
