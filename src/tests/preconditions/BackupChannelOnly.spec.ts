import { BackupChannelOnlyPrecondition } from '#preconditions/BackupChannelOnly';
import { UserError } from '@sapphire/framework';
import type { ChatInputCommandInteraction, Message } from 'discord.js';

// Mock the env utilities
jest.mock('@skyra/env-utilities', () => ({
	envParseString: jest.fn()
}));

import { envParseString } from '@skyra/env-utilities';

describe('BackupChannelOnly Precondition', () => {
	let precondition: BackupChannelOnlyPrecondition;
	const mockEnvParseString = envParseString as jest.MockedFunction<typeof envParseString>;

	beforeEach(() => {
		jest.clearAllMocks();

		precondition = new BackupChannelOnlyPrecondition({ name: 'BackupChannelOnly', path: '' } as any, {});
	});

	describe('ChatInput Commands', () => {
		it('should pass when no backup channel is configured', async () => {
			mockEnvParseString.mockReturnValue('');

			const mockInteraction = {
				channelId: '123456789'
			} as ChatInputCommandInteraction;

			const result = await precondition.chatInputRun(mockInteraction);

			expect(result.isOk()).toBe(true);
		});

		it('should pass when interaction is in the correct backup channel', async () => {
			mockEnvParseString.mockReturnValue('123456789');

			const mockInteraction = {
				channelId: '123456789'
			} as ChatInputCommandInteraction;

			const result = await precondition.chatInputRun(mockInteraction);

			expect(result.isOk()).toBe(true);
		});

		it('should fail when interaction is not in the backup channel', async () => {
			mockEnvParseString.mockReturnValue('123456789');

			const mockInteraction = {
				channelId: '987654321'
			} as ChatInputCommandInteraction;

			const result = await precondition.chatInputRun(mockInteraction);

			expect(result.isErr()).toBe(true);
			expect(result.unwrapErr()).toBeInstanceOf(UserError);
			expect(result.unwrapErr().message).toBe('❌ Backup commands can only be used in the designated backup channel.');
		});
	});

	describe('Message Commands', () => {
		it('should pass when no backup channel is configured', async () => {
			mockEnvParseString.mockReturnValue('');

			const mockMessage = {
				channelId: '123456789'
			} as Message;

			const result = await precondition.messageRun(mockMessage);

			expect(result.isOk()).toBe(true);
		});

		it('should pass when message is in the correct backup channel', async () => {
			mockEnvParseString.mockReturnValue('123456789');

			const mockMessage = {
				channelId: '123456789'
			} as Message;

			const result = await precondition.messageRun(mockMessage);

			expect(result.isOk()).toBe(true);
		});

		it('should fail when message is not in the backup channel', async () => {
			mockEnvParseString.mockReturnValue('123456789');

			const mockMessage = {
				channelId: '987654321'
			} as Message;

			const result = await precondition.messageRun(mockMessage);

			expect(result.isErr()).toBe(true);
			expect(result.unwrapErr()).toBeInstanceOf(UserError);
			expect(result.unwrapErr().message).toBe('❌ Backup commands can only be used in the designated backup channel.');
		});
	});
});
