import { GuildOnlyPrecondition } from '#preconditions/GuildOnly';
import { UserError } from '@sapphire/framework';
import type { ChatInputCommandInteraction, Guild } from 'discord.js';

describe('GuildOnly Precondition', () => {
	let precondition: GuildOnlyPrecondition;

	beforeEach(() => {
		jest.clearAllMocks();

		precondition = new GuildOnlyPrecondition({ name: 'GuildOnly', path: '' } as any, {});
	});

	it('should pass when interaction is in a guild', async () => {
		const mockInteraction = {
			guild: { id: '123456789' } as Guild
		} as ChatInputCommandInteraction;

		const result = await precondition.chatInputRun(mockInteraction);

		expect(result.isOk()).toBe(true);
	});

	it('should fail when interaction is not in a guild', async () => {
		const mockInteraction = {
			guild: null
		} as ChatInputCommandInteraction;

		const result = await precondition.chatInputRun(mockInteraction);

		expect(result.isErr()).toBe(true);
		expect(result.unwrapErr()).toBeInstanceOf(UserError);
		expect(result.unwrapErr().message).toBe('❌ This command can only be used in servers.');
	});
});
