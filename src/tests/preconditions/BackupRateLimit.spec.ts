import { BackupRateLimitPrecondition } from '#preconditions/BackupRateLimit';
import { UserError } from '@sapphire/framework';
import type { ChatInputCommandInteraction, User } from 'discord.js';

// Mock the env utilities
jest.mock('@skyra/env-utilities', () => ({
	envParseString: jest.fn()
}));

import { envParseString } from '@skyra/env-utilities';

describe('BackupRateLimit Precondition', () => {
	let precondition: BackupRateLimitPrecondition;
	const mockEnvParseString = envParseString as jest.MockedFunction<typeof envParseString>;

	beforeEach(() => {
		jest.clearAllMocks();

		precondition = new BackupRateLimitPrecondition({ name: 'BackupRateLimit', path: '' } as any, {});
	});	it('should pass when no rate limit is configured', async () => {
		mockEnvParseString.mockReturnValue('');

		const mockInteraction = {
			user: { id: '123456789' } as User
		} as ChatInputCommandInteraction;

		const result = await precondition.chatInputRun(mockInteraction);

		expect(result.isOk()).toBe(true);
	});

	it('should pass for first command from user', async () => {
		mockEnvParseString.mockReturnValue('5');

		const mockInteraction = {
			user: { id: '123456789' } as User
		} as ChatInputCommandInteraction;

		const result = await precondition.chatInputRun(mockInteraction);

		expect(result.isOk()).toBe(true);
	});

	it('should fail when user exceeds rate limit', async () => {
		mockEnvParseString.mockReturnValue('5');

		const mockInteraction = {
			user: { id: '123456789' } as User
		} as ChatInputCommandInteraction;

		// First command should pass
		let result = await precondition.chatInputRun(mockInteraction);
		expect(result.isOk()).toBe(true);

		// Second command immediately should fail
		result = await precondition.chatInputRun(mockInteraction);
		expect(result.isErr()).toBe(true);
		expect(result.unwrapErr()).toBeInstanceOf(UserError);
		expect(result.unwrapErr().message).toContain('Please wait');
	});

	it('should pass after cooldown period', async () => {
		mockEnvParseString.mockReturnValue('0.01'); // 0.01 minutes = 0.6 seconds

		const mockInteraction = {
			user: { id: '123456789' } as User
		} as ChatInputCommandInteraction;

		// First command should pass
		let result = await precondition.chatInputRun(mockInteraction);
		expect(result.isOk()).toBe(true);

		// Wait for cooldown to expire
		await new Promise(resolve => setTimeout(resolve, 700));

		// Second command should now pass
		result = await precondition.chatInputRun(mockInteraction);
		expect(result.isOk()).toBe(true);
	});
});
