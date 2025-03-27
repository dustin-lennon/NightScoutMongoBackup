/* eslint-disable @typescript-eslint/no-require-imports */

jest.mock('discord.js', () => {
	const original = jest.requireActual('discord.js');
	return {
		...original,
		ClientUser: function ClientUserMock() {}
	};
});

import { Command, Listener } from '@sapphire/framework';
import { mockLogger } from './__mocks__/mockLogger';

jest.mock('@sentry/node');

describe('Sentry Integration Tests', () => {
	beforeEach(() => {
		jest.resetModules(); // ensure fresh state
		jest.clearAllMocks();
		jest.restoreAllMocks();

		// Suppress logger output during tests
		jest.spyOn(console, 'error').mockImplementation(() => {});
	});

	test('initializes Sentry correctly', () => {
		jest.isolateModules(() => {
			// Mocks moved to top of file

			const Sentry = require('@sentry/node');
			process.env.SENTRY_DSN = 'https://fake@dsn/123';
			process.env.NODE_ENV = 'test';

			const index = require('../index');
			index.startBot();
			const client = index.client;

			index.attachErrorHandlers();
			client.logger = mockLogger;

			expect(Sentry.init).toHaveBeenCalledWith(
				expect.objectContaining({
					dsn: process.env.SENTRY_DSN,
					environment: process.env.NODE_ENV || 'development',
					tracesSampleRate: 1.0
				})
			);
		});
	});

	test('captures unhandled promise rejections', () => {
		jest.isolateModules(() => {
			// Mocks moved to top of file

			process.env.SENTRY_DSN = 'https://fake@dsn/123';
			process.env.NODE_ENV = 'test';

			const Sentry = require('@sentry/node');
			const index = require('../index');
			index.startBot(); // ← This initializes `client`
			const client = index.client;

			index.attachErrorHandlers();
			client.logger = mockLogger;

			const rejectionError = new Error('Test rejection');
			process.listeners('unhandledRejection').forEach((listener) =>
				listener(rejectionError, Promise.resolve())
			);

			expect(Sentry.captureException).toHaveBeenCalledWith(rejectionError);
		});
	});

	test('captures uncaught exceptions', () => {
		jest.isolateModules(() => {
			// Mocks moved to top of file

			process.env.SENTRY_DSN = 'https://fake@dsn/123';
			process.env.NODE_ENV = 'test';

			const Sentry = require('@sentry/node');
			const index = require('../index');
			index.startBot(); // initialize client
			const client = index.client;

			index.attachErrorHandlers();
			client.logger = mockLogger;

			const exceptionError = new Error('Test exception');
			process.listeners('uncaughtException').forEach((listener) =>
				listener(exceptionError, 'uncaughtException')
			);

			expect(Sentry.captureException).toHaveBeenCalledWith(exceptionError);
		});
	});

	test('creates breadcrumb on command execution', () => {
		jest.isolateModules(() => {
			// Mocks moved to top of file

			const Sentry = require('@sentry/node');
			process.env.SENTRY_DSN = 'https://fake@dsn/123';
			process.env.NODE_ENV = 'test';

			const context = {
				name: 'commandExecuted',
				path: '',
				root: '',
				store: {
					container: {}
				}
			} as unknown as Listener.LoaderContext;

			const { CommandExecutedListener } = require('../events/commandExecuted');
			const listener = new CommandExecutedListener(context, {
				event: 'commandExecuted',
				logger: mockLogger
			});

			const mockCommand = { name: 'testCommand' } as Command;

			listener.run(mockCommand);

			expect(Sentry.addBreadcrumb).toHaveBeenCalledWith({
				category: 'commands',
				message: `Executed ${mockCommand.name}`,
				level: 'info'
			});

			expect(mockLogger.info).toHaveBeenCalledWith(`Executed command: ${mockCommand.name}`);
		});
	});
});
