jest.mock('discord.js', () => {
	const original = jest.requireActual('discord.js');
	return {
		...original,
		ClientUser: function () {
			return {
				id: '123',
				username: 'MockUser',
				tag: 'MockUser#0001'
			};
		},
		WebSocketManager: class {},
		WebSocketShard: class {},
		Guild: class {},
		GuildManager: class {},
		ChannelManager: class {}
	};
});

import { mockLogger } from './__mocks__/mockLogger';
import { attachErrorHandlers, startBot } from '../index';
import { SapphireClient } from '@sapphire/framework';

describe('Coverage Utility', () => {
	beforeAll(() => {
		attachErrorHandlers();
	});

	beforeEach(() => {
		jest.spyOn(SapphireClient.prototype, 'login').mockImplementation(() => Promise.resolve('mock-token'));
		jest.spyOn(console, 'error').mockImplementation(() => {});
	});

	it('simulates a handled unhandledRejection', () => {
		const { client } = startBot();
		(client as any).logger = mockLogger; // Override readonly for test
		const testReason = new Error('Simulated rejection');
		(process as NodeJS.EventEmitter).emit('unhandledRejection', testReason);
		expect(mockLogger.error).toHaveBeenCalledWith('Unhandled Rejection:', testReason);
	});

	it('simulates a handled uncaughtException', () => {
		const { client } = startBot();
		(client as any).logger = mockLogger; // Override readonly for test
		const testError = new Error('Simulated exception');
		process.emit('uncaughtException', testError);
		expect(mockLogger.error).toHaveBeenCalledWith('Uncaught Exception:', testError);
	});
});
