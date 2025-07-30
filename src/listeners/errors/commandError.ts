import { Listener } from '@sapphire/framework';
import * as Sentry from '@sentry/node';

export class CommandErrorListener extends Listener {
	public constructor(context: Listener.LoaderContext, options: Listener.Options) {
		super(context, {
			...options,
			event: 'commandError'
		});
	}

	public run(error: Error, context: any) {
		const commandName = context?.command?.name || 'unknown';
		this.container.logger.error(`Command ${commandName} encountered an error:`, error);

		Sentry.captureException(error, {
			tags: {
				type: 'command_error',
				command: commandName
			}
		});
	}
}
