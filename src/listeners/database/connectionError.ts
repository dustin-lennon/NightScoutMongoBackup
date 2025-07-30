import { Listener } from '@sapphire/framework';
import * as Sentry from '@sentry/node';

export class DatabaseConnectionErrorListener extends Listener {
	public constructor(context: Listener.LoaderContext, options: Listener.Options) {
		super(context, {
			...options,
			event: 'mongoConnectionError'
		});
	}

	public run(error: Error) {
		this.container.logger.error('MongoDB connection error:', error);

		Sentry.captureException(error, {
			tags: {
				type: 'database_connection_error'
			}
		});
	}
}
