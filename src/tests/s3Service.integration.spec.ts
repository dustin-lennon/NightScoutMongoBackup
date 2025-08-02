import { S3Service } from '../lib/services/s3';
import { S3Client, ListObjectsV2Command } from '@aws-sdk/client-s3';
import * as fs from 'fs';
import * as path from 'path';

describe('S3Service Integration Tests', () => {
	let s3Service: S3Service;

	// Check if AWS credentials are available
	const hasAWSCredentials = !!(
		process.env.AWS_ACCESS_KEY_ID &&
		process.env.AWS_SECRET_ACCESS_KEY &&
		process.env.AWS_REGION &&
		process.env.S3_BACKUP_BUCKET
	);

	beforeAll(() => {
		if (hasAWSCredentials) {
			console.log('AWS Integration Tests: Credentials detected');
			console.log(`Access Key: ${process.env.AWS_ACCESS_KEY_ID?.substring(0, 8)}...`);
			console.log(`Region: ${process.env.AWS_REGION}`);
			console.log(`Bucket: ${process.env.S3_BACKUP_BUCKET}`);
			s3Service = new S3Service();
		} else {
			console.log('AWS Integration Tests: No credentials found - tests will be skipped');
		}
	});

	(hasAWSCredentials ? it : it.skip)('should authenticate with real AWS credentials', async () => {
		// Test basic S3 connectivity
		const client = new S3Client({
			region: s3Service.getRegion(),
			credentials: {
				accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
				secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!
			}
		});

		const command = new ListObjectsV2Command({
			Bucket: s3Service.getBucketName(),
			MaxKeys: 1
		});

		// This should not throw an error if credentials are valid
		const result = await client.send(command);
		expect(result).toBeDefined();
		expect(result.Name).toBe(s3Service.getBucketName());
	}, 10000);

	(hasAWSCredentials ? it : it.skip)('should handle authentication failures gracefully', async () => {
		// Test with intentionally bad credentials
		const client = new S3Client({
			region: s3Service.getRegion(),
			credentials: {
				accessKeyId: 'INVALID_KEY',
				secretAccessKey: 'INVALID_SECRET'
			}
		});

		const command = new ListObjectsV2Command({
			Bucket: s3Service.getBucketName(),
			MaxKeys: 1
		});

		await expect(client.send(command)).rejects.toThrow();
	}, 10000);

	(hasAWSCredentials ? it : it.skip)('should test actual file upload and cleanup', async () => {
		// Create a temporary test file
		const testData = {
			testField: 'integration-test-data',
			timestamp: new Date().toISOString(),
			testId: Math.random().toString(36).substring(7)
		};

		const tempDir = path.join(__dirname, '../..', 'temp');
		if (!fs.existsSync(tempDir)) {
			fs.mkdirSync(tempDir, { recursive: true });
		}

		const testFilePath = path.join(tempDir, `integration-test-${testData.testId}.json`);

		try {
			// Write test file
			fs.writeFileSync(testFilePath, JSON.stringify(testData, null, 2));

			// Upload the file
			const uploadResult = await s3Service.uploadFile(testFilePath);

			expect(uploadResult).toBeDefined();
			expect(uploadResult.success).toBe(true);
			expect(uploadResult.key).toBeDefined();
			expect(uploadResult.s3Url).toContain(s3Service.getBucketName());

			// Verify upload was successful by checking if object exists
			const client = new S3Client({
				region: s3Service.getRegion(),
				credentials: {
					accessKeyId: process.env.AWS_ACCESS_KEY_ID!,
					secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY!
				}
			});

			const listCommand = new ListObjectsV2Command({
				Bucket: s3Service.getBucketName(),
				Prefix: uploadResult.key!,
				MaxKeys: 1
			});

			const listResult = await client.send(listCommand);
			expect(listResult.Contents).toBeDefined();
			expect(listResult.Contents?.length).toBeGreaterThan(0);
			expect(listResult.Contents?.[0]?.Key).toBe(uploadResult.key);

			// Clean up - delete the uploaded file
			await s3Service.deleteObject(uploadResult.key!);
			console.log(`Cleaned up S3 object: ${uploadResult.key}`);

		} finally {
			// Clean up local test file
			if (fs.existsSync(testFilePath)) {
				fs.unlinkSync(testFilePath);
			}

			// Clean up temp directory if empty
			try {
				if (fs.existsSync(tempDir) && fs.readdirSync(tempDir).length === 0) {
					fs.rmdirSync(tempDir);
				}
			} catch (error) {
				// Ignore cleanup errors
			}
		}
	}, 15000);
});
