import { CommandErrorListener } from '#listeners/errors/commandError';
import * as Sentry from '@sentry/node';
import type { ChatInputCommandErrorPayload } from '@sapphire/framework';

// Mock Sentry
jest.mock('@sentry/node', () => ({
	captureException: jest.fn()
}));

describe('CommandError Listener', () => {
	let listener: CommandErrorListener;
	const mockCaptureException = Sentry.captureException as jest.MockedFunction<typeof Sentry.captureException>;
	const mockLogger = {
		error: jest.fn()
	};

	beforeEach(() => {
		jest.clearAllMocks();

		listener = new CommandErrorListener({ name: 'commandError', path: '' } as any, {});
		// Mock the container property
		Object.defineProperty(listener, 'container', {
			value: {
				logger: mockLogger
			},
			writable: false
		});
	});	it('should log and capture error', () => {
		const mockError = new Error('Test error');
		const mockPayload = {
			command: { name: 'backup' },
			interaction: { user: { id: '123456789' } }
		} as ChatInputCommandErrorPayload;

		listener.run(mockError, mockPayload);

		expect(mockLogger.error).toHaveBeenCalledWith('Command backup encountered an error:', mockError);
		expect(mockCaptureException).toHaveBeenCalledWith(mockError, {
			tags: {
				type: 'command_error',
				command: 'backup'
			}
		});
	});

	it('should handle missing command name', () => {
		const mockError = new Error('Test error');
		const mockPayload = {
			command: { name: undefined },
			interaction: { user: { id: '123456789' } }
		} as any;

		listener.run(mockError, mockPayload);

		expect(mockLogger.error).toHaveBeenCalledWith('Command unknown encountered an error:', mockError);
		expect(mockCaptureException).toHaveBeenCalledWith(mockError, {
			tags: {
				type: 'command_error',
				command: 'unknown'
			}
		});
	});
});
