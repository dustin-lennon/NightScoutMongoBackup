import { Listener, container } from '@sapphire/framework';
import type { Command } from '@sapphire/framework';
import * as Sentry from '@sentry/node';

// Use the container logger type here without referencing `this`
type LoggerType = typeof container.logger;

export class CommandExecutedListener extends Listener {
	private readonly logger: LoggerType;

	public constructor(
		context: Listener.LoaderContext,
		options: Listener.Options & { logger?: LoggerType } = {}
	) {
		super(context, { ...options, event: 'commandExecuted' });

		// ✅ Now safe to reference container.logger
		this.logger = options.logger ?? container.logger;
	}

	public run(command: Command) {
		Sentry.addBreadcrumb({
			category: 'commands',
			message: `Executed ${command.name}`,
			level: 'info'
		});

		this.logger.info(`Executed command: ${command.name}`);
	}
}
