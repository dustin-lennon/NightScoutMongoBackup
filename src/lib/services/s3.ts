import { S3Client, PutObjectCommand, PutObjectCommandInput, DeleteObjectCommand, ListObjectsV2Command, ListObjectsV2CommandInput } from '@aws-sdk/client-s3';
import { envParseString } from '@skyra/env-utilities';
import { createReadStream } from 'fs';
import * as fs from 'fs/promises';
import * as path from 'path';
import { container } from '@sapphire/framework';

export interface S3UploadResult {
	success: boolean;
	s3Url?: string;
	key?: string;
	bucket?: string;
	error?: string;
}

export interface S3BackupFile {
	fileName: string;
	key: string;
	size: number;
	lastModified: Date;
	downloadUrl: string;
	etag: string;
	storageClass?: string;
}

export interface S3ListResult {
	success: boolean;
	files: S3BackupFile[];
	totalFiles: number;
	error?: string;
}

export class S3Service {
	private s3Client: S3Client;
	private readonly bucket: string;
	private readonly region: string;

	constructor() {
		this.region = envParseString('AWS_REGION', 'us-east-1');
		this.bucket = envParseString('S3_BACKUP_BUCKET', 'nightscout-backups');

		this.s3Client = new S3Client({
			region: this.region,
			credentials: {
				accessKeyId: envParseString('AWS_ACCESS_KEY_ID', ''),
				secretAccessKey: envParseString('AWS_SECRET_ACCESS_KEY', '')
			}
		});
	}

	async uploadFile(filePath: string): Promise<S3UploadResult> {
		try {
			const fileName = path.basename(filePath);
			const timestamp = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
			const key = `backups/${timestamp}/${fileName}`;

			// Read file for upload
			const fileStream = createReadStream(filePath);
			const fileStats = await fs.stat(filePath);

			const uploadParams: PutObjectCommandInput = {
				Bucket: this.bucket,
				Key: key,
				Body: fileStream,
				ContentLength: fileStats.size,
				ContentType: this.getContentType(fileName),
				ACL: 'public-read', // Public read access as requested
				Metadata: {
					'backup-timestamp': new Date().toISOString(),
					'file-size': fileStats.size.toString()
				}
			};

			const command = new PutObjectCommand(uploadParams);
			await this.s3Client.send(command);

			const s3Url = `https://${this.bucket}.s3.${this.region}.amazonaws.com/${key}`;

			return {
				success: true,
				s3Url,
				key,
				bucket: this.bucket
			};
		} catch (error) {
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Unknown S3 upload error'
			};
		}
	}

	private getContentType(fileName: string): string {
		const ext = path.extname(fileName).toLowerCase();
		switch (ext) {
			case '.json':
				return 'application/json';
			case '.gz':
				return 'application/gzip';
			case '.br':
				return 'application/brotli';
			case '.7z':
				return 'application/x-7z-compressed';
			default:
				return 'application/octet-stream';
		}
	}

	async deleteObject(key: string): Promise<void> {
		try {
			const command = new DeleteObjectCommand({
				Bucket: this.bucket,
				Key: key
			});
			await this.s3Client.send(command);
		} catch (error) {
			container.logger.error(`Failed to delete S3 object ${key}:`, error);
		}
	}

	async listBackups(): Promise<S3ListResult> {
		try {
			const listParams: ListObjectsV2CommandInput = {
				Bucket: this.bucket,
				Prefix: 'backups/', // Only list files in the backups folder
				MaxKeys: 1000 // Limit to prevent huge responses
			};

			const command = new ListObjectsV2Command(listParams);
			const response = await this.s3Client.send(command);

			const files: S3BackupFile[] = (response.Contents || []).map(obj => ({
				fileName: obj.Key?.split('/').pop() || 'unknown',
				key: obj.Key || '',
				size: obj.Size || 0,
				lastModified: obj.LastModified || new Date(),
				downloadUrl: `https://${this.bucket}.s3.${this.region}.amazonaws.com/${obj.Key}`,
				etag: obj.ETag?.replace(/"/g, '') || '',
				storageClass: obj.StorageClass
			}));

			// Sort by last modified date (newest first)
			files.sort((a, b) => b.lastModified.getTime() - a.lastModified.getTime());

			return {
				success: true,
				files,
				totalFiles: files.length
			};
		} catch (error) {
			return {
				success: false,
				files: [],
				totalFiles: 0,
				error: error instanceof Error ? error.message : 'Unknown S3 list error'
			};
		}
	}

	getBucketName(): string {
		return this.bucket;
	}

	getRegion(): string {
		return this.region;
	}
}

export const s3Service = new S3Service();
