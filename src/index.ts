import * as Sentry from '@sentry/node';
import { GatewayIntentBits } from 'discord.js';
import { LogLevel, SapphireClient } from '@sapphire/framework';
import 'dotenv/config';
import '@sentry/tracing';
import { nodeProfilingIntegration } from '@sentry/profiling-node';

let internalClient: SapphireClient;

export function startBot(): { client: SapphireClient } {
	Sentry.init({
		dsn: process.env.SENTRY_DSN,
		environment: process.env.NODE_ENV ?? 'development',
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
	});

	/* istanbul ignore else */
	if (process.env.NODE_ENV !== 'test') {
		attachErrorHandlers();

		/* istanbul ignore next */
		internalClient
			.login(process.env.DISCORD_TOKEN)
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
if (!process.env.JEST_WORKER_ID && !process.env.SKIP_ERROR_HANDLERS) {
	startBot();
}
