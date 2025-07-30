import '#lib/setup';

import * as Sentry from '@sentry/node';
import { envParseString } from '@skyra/env-utilities';
import { GatewayIntentBits } from 'discord.js';
import { LogLevel, SapphireClient } from '@sapphire/framework';
import 'dotenv/config';
import '@sentry/tracing';
import { nodeProfilingIntegration } from '@sentry/profiling-node';
import { NightlyBackupTask } from '#scheduled-tasks/nightlyBackup';

let internalClient: SapphireClient;

export function startBot(): { client: SapphireClient } {
	Sentry.init({
		dsn: envParseString('SENTRY_DSN'),
		environment: envParseString('NODE_ENV', 'development'),
		tracesSampleRate: 1.0,
		profilesSampleRate: 1.0,
		integrations: [
			nodeProfilingIntegration(),
		]
	});

	internalClient = new SapphireClient({
		intents: [
			GatewayIntentBits.Guilds,
			GatewayIntentBits.MessageContent
		],
		logger: { level: LogLevel.Info }
	});

	/* istanbul ignore next */
	internalClient.once('ready', () => {
		console.log(`✅ Bot is online as ${internalClient.user?.tag}!`);

		// Start nightly backup task when bot is ready
		if (envParseString('NODE_ENV', 'development') !== 'test') {
			const nightlyBackupTask = new NightlyBackupTask();
			nightlyBackupTask.start();
		}
	});

	/* istanbul ignore else */
	if (envParseString('NODE_ENV', 'development') !== 'test') {
		attachErrorHandlers();

		/* istanbul ignore next */
		internalClient
			.login(envParseString('DISCORD_TOKEN'))
			.catch((error) => {
				Sentry.captureException(error);
				console.error('❌ Failed to login:', error);
			});
	}

	return { client: internalClient };
}

export function attachErrorHandlers(): void {
	process.on('unhandledRejection', (reason) => {
		Sentry.captureException(reason);
		internalClient.logger.error('Unhandled Rejection:', reason);
	});

	process.on('uncaughtException', (error) => {
		Sentry.captureException(error);
		internalClient.logger.error('Uncaught Exception:', error);
	});
}

/* istanbul ignore next */
if (!envParseString('JEST_WORKER_ID', '') && !envParseString('SKIP_ERROR_HANDLERS', '')) {
	startBot();
}
