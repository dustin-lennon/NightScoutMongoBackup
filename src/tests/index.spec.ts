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
			logger: {
				error: jest.fn()
			}
		}))
	};
});

describe('startBot()', () => {
	beforeEach(() => {
		jest.resetModules();
		jest.clearAllMocks();
		process.env.SENTRY_DSN = 'https://fake@dsn/123';
		process.env.NODE_ENV = 'test';
		process.env.DISCORD_TOKEN = 'fake-token';
	});

	it('initializes Sentry and logs in the bot', async () => {
		const { startBot } = require('../index');
		await startBot();

		const Sentry = require('@sentry/node');
		expect(Sentry.init).toHaveBeenCalledWith(
			expect.objectContaining({
				dsn: 'https://fake@dsn/123',
				environment: 'test',
				tracesSampleRate: 1.0
			})
		);
	});
});
