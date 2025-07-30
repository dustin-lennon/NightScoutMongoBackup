import { DatabaseConnectionErrorListener } from '#listeners/database/connectionError';
import * as Sentry from '@sentry/node';

// Mock Sentry
jest.mock('@sentry/node', () => ({
	captureException: jest.fn()
}));

describe('DatabaseConnectionError Listener', () => {
	let listener: DatabaseConnectionErrorListener;
	const mockCaptureException = Sentry.captureException as jest.MockedFunction<typeof Sentry.captureException>;
	const mockLogger = {
		error: jest.fn()
	};

	beforeEach(() => {
		jest.clearAllMocks();

		listener = new DatabaseConnectionErrorListener({ name: 'mongoConnectionError', path: '' } as any, {});
		// Mock the container property
		Object.defineProperty(listener, 'container', {
			value: {
				logger: mockLogger
			},
			writable: false
		});
	});

	it('should log and capture MongoDB connection error', () => {
		const mockError = new Error('Connection timeout');

		listener.run(mockError);

		expect(mockLogger.error).toHaveBeenCalledWith('MongoDB connection error:', mockError);
		expect(mockCaptureException).toHaveBeenCalledWith(mockError, {
			tags: {
				type: 'database_connection_error'
			}
		});
	});
});
