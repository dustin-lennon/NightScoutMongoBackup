import * as Sentry from '@sentry/node';
import { GatewayIntentBits } from 'discord.js';
import { LogLevel, SapphireClient } from '@sapphire/framework';
import 'dotenv/config';
import '@sentry/tracing';

Sentry.init({
	dsn: process.env.SENTRY_DSN,
	environment: process.env.NODE_ENV || 'development',
	tracesSampleRate: 1.0
});

export const client = new SapphireClient({
	intents: [GatewayIntentBits.Guilds],
	logger: { level: LogLevel.Info }
});

client.once('ready', () => {
	console.log(`✅ Bot is online as ${client.user?.tag}!`);
});

export function attachErrorHandlers(): void {
	process.on('unhandledRejection', (reason) => {
		Sentry.captureException(reason);
		client.logger.error('Unhandled Rejection:', reason);
	});

	process.on('uncaughtException', (error) => {
		Sentry.captureException(error);
		client.logger.error('Uncaught Exception:', error);
	});
}

// Attach automatically in production
if (!process.env.JEST_WORKER_ID && !process.env.SKIP_ERROR_HANDLERS) {
	client
		.login(process.env.DISCORD_TOKEN)
		.then(() => attachErrorHandlers())
		.catch((error) => {
			Sentry.captureException(error);
			console.error('❌ Failed to login:', error);
		});
}
