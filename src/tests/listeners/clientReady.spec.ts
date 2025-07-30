import { ClientReadyListener } from '#listeners/client/clientReady';
import type { Client } from 'discord.js';

describe('ClientReady Listener', () => {
	let listener: ClientReadyListener;
	const mockLogger = {
		info: jest.fn()
	};
	const mockClient = {
		user: {
			setActivity: jest.fn()
		}
	} as unknown as Client;

	beforeEach(() => {
		jest.clearAllMocks();

		listener = new ClientReadyListener({ name: 'ready', path: '' } as any, {});
		// Mock the container property
		Object.defineProperty(listener, 'container', {
			value: {
				logger: mockLogger,
				client: mockClient
			},
			writable: false
		});
	});	it('should log ready message and set activity', () => {
		listener.run();

		expect(mockLogger.info).toHaveBeenCalled();
		expect(mockClient.user?.setActivity).toHaveBeenCalledWith('🗄️ Backing up NightScout data', { type: 3 });
	});
});
