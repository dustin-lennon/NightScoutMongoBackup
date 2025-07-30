declare module '@skyra/env-utilities' {
	interface Env {
		// MongoDB Configuration
		MONGO_USERNAME?: string;
		MONGO_PASSWORD?: string;
		MONGO_HOST?: string;
		MONGO_DB?: string;
		MONGO_API_KEY?: string;

		// Discord Configuration
		DISCORD_TOKEN?: string;
		BACKUP_CHANNEL_ID?: string;

		// AWS/S3 Configuration
		AWS_REGION?: string;
		AWS_ACCESS_KEY_ID?: string;
		AWS_SECRET_ACCESS_KEY?: string;
		S3_BACKUP_BUCKET?: string;

		// Sentry Configuration
		SENTRY_DSN?: string;

		// Application Configuration
		ENABLE_NIGHTLY_BACKUP?: string;
		BACKUP_HOUR?: string;
		BACKUP_MINUTE?: string;
		BACKUP_RATE_LIMIT_MINUTES?: string;

		// Testing Environment Variables
		JEST_WORKER_ID?: string;
		SKIP_ERROR_HANDLERS?: string;
		ENABLE_TEST_ERROR_HANDLERS?: string;
	}
}
