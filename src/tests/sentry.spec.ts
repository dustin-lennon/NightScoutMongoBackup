/* eslint-disable @typescript-eslint/no-require-imports */

jest.mock('@sentry/node');

import { Command, Listener } from '@sapphire/framework';
import { mockLogger } from './__mocks__/mockLogger';


describe('Sentry Integration Tests', () => {
	beforeEach(() => {
		jest.resetModules(); // ensure fresh state
		jest.clearAllMocks();

		// Suppress logger output during tests
		jest.spyOn(console, 'error').mockImplementation(() => {});
	});

	test('initializes Sentry correctly', () => {
		jest.isolateModules(() => {
			const Sentry = require('@sentry/node');
			process.env.SENTRY_DSN = 'https://fake@dsn/123';
			process.env.NODE_ENV = 'test';

			require('../index');

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
			process.env.SENTRY_DSN = 'https://fake@dsn/123';
			process.env.NODE_ENV = 'test';

			const Sentry = require('@sentry/node');
			const { attachErrorHandlers } = require('../index');
			attachErrorHandlers();

			const rejectionError = new Error('Test rejection');
			process.listeners('unhandledRejection').forEach((listener) =>
				listener(rejectionError, Promise.resolve())
			);

			expect(Sentry.captureException).toHaveBeenCalledWith(rejectionError);
		});
	});

	test('captures uncaught exceptions', async () => {
		const exceptionError = new Error('Test exception');

		jest.isolateModules(() => {
			process.env.SENTRY_DSN = 'https://fake@dsn/123';
			process.env.NODE_ENV = 'test';

			const Sentry = require('@sentry/node');
			const { attachErrorHandlers } = require('../index');
			attachErrorHandlers();

			const exceptionError = new Error('Test exception');
			process.listeners('uncaughtException').forEach((listener) =>
				listener(exceptionError, 'uncaughtException')
			);

			expect(Sentry.captureException).toHaveBeenCalledWith(exceptionError);
		});
	});

	test('creates breadcrumb on command execution', () => {
		jest.isolateModules(() => {
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
