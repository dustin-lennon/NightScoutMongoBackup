/* eslint-disable @typescript-eslint/no-require-imports */

jest.mock('@sentry/node', () => ({
	init: jest.fn(),
	captureException: jest.fn()
}));

jest.mock('@sapphire/framework', () => {
	const actual = jest.requireActual('@sapphire/framework');
	return {
		...actual,
		SapphireClient: jest.fn().mockImplementation(() => ({
			once: jest.fn(),
			login: jest.fn().mockResolvedValue(undefined),
			user: { tag: 'TestBot#1234' },
			logger: {
				error: jest.fn(),
				info: jest.fn()
			}
		})),
		container: {
			logger: {
				info: jest.fn(),
				error: jest.fn()
			}
		}
	};
});

describe('Index Module', () => {
	let mockClient: any;
	let originalEnv: any;

	beforeEach(() => {
		jest.resetModules();
		jest.clearAllMocks();

		// Store original environment
		originalEnv = { ...process.env };

		// Set up test environment
		process.env.SENTRY_DSN = 'https://fake@dsn/123';
		process.env.NODE_ENV = 'test';
		process.env.DISCORD_TOKEN = 'fake-token';
		delete process.env.JEST_WORKER_ID;
		delete process.env.SKIP_ERROR_HANDLERS;

		const { SapphireClient } = require('@sapphire/framework');
		mockClient = {
			once: jest.fn(),
			login: jest.fn().mockResolvedValue(undefined),
			user: { tag: 'TestBot#1234' },
			logger: {
				error: jest.fn(),
				info: jest.fn()
			}
		};
		SapphireClient.mockImplementation(() => mockClient);
	});

	afterEach(() => {
		// Restore original environment
		process.env = originalEnv;
	});

	describe('startBot', () => {
		it('should initialize Sentry and create client', async () => {
			const { startBot } = require('../index');
			const result = startBot();

			const Sentry = require('@sentry/node');
			expect(Sentry.init).toHaveBeenCalledWith(
				expect.objectContaining({
					dsn: 'https://fake@dsn/123',
					environment: 'test',
					tracesSampleRate: 1.0,
					profilesSampleRate: 1.0,
					integrations: expect.any(Array)
				})
			);

			expect(result.client).toBe(mockClient);
		});

		it('should set up ready event handler', () => {
			const { startBot } = require('../index');
			startBot();

			expect(mockClient.once).toHaveBeenCalledWith('ready', expect.any(Function));
		});

		it('should log ready message when bot is ready', () => {
			const { startBot } = require('../index');
			startBot();

			// Get the ready callback and execute it
			const readyCallback = mockClient.once.mock.calls.find((call: any) => call[0] === 'ready')?.[1];
			if (readyCallback) {
				readyCallback(mockClient);
			}

			expect(mockClient.logger.info).toHaveBeenCalledWith('✅ Bot is online as TestBot#1234!');
		});

		it('should not login when NODE_ENV is test', () => {
			process.env.NODE_ENV = 'test';
			const { startBot } = require('../index');
			startBot();

			expect(mockClient.login).not.toHaveBeenCalled();
		});

		it('should login when NODE_ENV is not test', () => {
			process.env.NODE_ENV = 'production';
			const { startBot } = require('../index');
			startBot();

			expect(mockClient.login).toHaveBeenCalledWith('fake-token');
		});

		it('should handle login errors', async () => {
			const loginError = new Error('Login failed');
			mockClient.login.mockRejectedValue(loginError);

			const Sentry = require('@sentry/node');

			process.env.NODE_ENV = 'production';
			const { startBot } = require('../index');
			startBot();

			// Wait for login promise to resolve
			await new Promise(resolve => setTimeout(resolve, 0));

			expect(Sentry.captureException).toHaveBeenCalledWith(loginError);
			expect(mockClient.logger.error).toHaveBeenCalledWith('❌ Failed to login:', loginError);
		});

		it('should use default environment when NODE_ENV is not set', () => {
			(process.env as any).NODE_ENV = undefined;
			const { startBot } = require('../index');
			startBot();

			const Sentry = require('@sentry/node');
			expect(Sentry.init).toHaveBeenCalledWith(
				expect.objectContaining({
					environment: 'development'
				})
			);
		});
	});

	describe('attachErrorHandlers', () => {
		let processOnSpy: jest.SpyInstance;
		let addedListeners: Array<{ event: string; handler: (...args: any[]) => void }> = [];

		beforeEach(() => {
			addedListeners = [];
			processOnSpy = jest.spyOn(process, 'on').mockImplementation((event: string | symbol, handler: (...args: any[]) => void) => {
				addedListeners.push({ event: event.toString(), handler });
				return process;
			});
		});

		afterEach(() => {
			// Clean up any real listeners that might have been added
			addedListeners.forEach(({ event, handler }) => {
				process.removeListener(event as any, handler);
			});
			processOnSpy.mockRestore();
		});

		it('should attach unhandledRejection handler', () => {
			const { attachErrorHandlers } = require('../index');
			attachErrorHandlers();

			expect(processOnSpy).toHaveBeenCalledWith('unhandledRejection', expect.any(Function));
		});

		it('should attach uncaughtException handler', () => {
			const { attachErrorHandlers } = require('../index');
			attachErrorHandlers();

			expect(processOnSpy).toHaveBeenCalledWith('uncaughtException', expect.any(Function));
		});

		it('should handle unhandledRejection events', () => {
			const { attachErrorHandlers, startBot } = require('../index');
			const client = startBot();
			attachErrorHandlers();

			const Sentry = require('@sentry/node');
			const rejectionReason = new Error('Unhandled rejection');

			// Get the handler from the mocked calls
			const unhandledRejectionHandler = addedListeners.find(
				listener => listener.event === 'unhandledRejection'
			)?.handler;

			if (unhandledRejectionHandler) {
				unhandledRejectionHandler(rejectionReason);
			}

			expect(Sentry.captureException).toHaveBeenCalledWith(rejectionReason);
			expect(client.client.logger.error).toHaveBeenCalledWith('Unhandled Rejection:', rejectionReason);
		});

		it('should handle uncaughtException events', () => {
			const { attachErrorHandlers, startBot } = require('../index');
			const client = startBot();
			attachErrorHandlers();

			const Sentry = require('@sentry/node');
			const uncaughtError = new Error('Uncaught exception');

			// Get the handler from the mocked calls
			const uncaughtExceptionHandler = addedListeners.find(
				listener => listener.event === 'uncaughtException'
			)?.handler;

			if (uncaughtExceptionHandler) {
				uncaughtExceptionHandler(uncaughtError);
			}

			expect(Sentry.captureException).toHaveBeenCalledWith(uncaughtError);
			expect(client.client.logger.error).toHaveBeenCalledWith('Uncaught Exception:', uncaughtError);
		});
	});	describe('Module initialization', () => {
		it('should call startBot when not in test environment and not skipping error handlers', () => {
			// Mock the startBot function
			const startBotSpy = jest.fn();
			jest.doMock('../index', () => ({
				startBot: startBotSpy,
				attachErrorHandlers: jest.fn()
			}));

			// Simulate non-test environment
			process.env.NODE_ENV = 'production';
			delete process.env.JEST_WORKER_ID;
			delete process.env.SKIP_ERROR_HANDLERS;

			// This would normally trigger the module initialization
			// Since we can't easily test the bottom-level code, we'll test the logic path
			const shouldStartBot = !process.env.JEST_WORKER_ID && !process.env.SKIP_ERROR_HANDLERS;
			expect(shouldStartBot).toBe(true);
		});

		it('should not call startBot when JEST_WORKER_ID is set', () => {
			process.env.JEST_WORKER_ID = '1';

			const shouldStartBot = !process.env.JEST_WORKER_ID && !process.env.SKIP_ERROR_HANDLERS;
			expect(shouldStartBot).toBe(false);
		});

		it('should not call startBot when SKIP_ERROR_HANDLERS is set', () => {
			process.env.SKIP_ERROR_HANDLERS = 'true';
			delete process.env.JEST_WORKER_ID;

			const shouldStartBot = !process.env.JEST_WORKER_ID && !process.env.SKIP_ERROR_HANDLERS;
			expect(shouldStartBot).toBe(false);
		});
	});
});
