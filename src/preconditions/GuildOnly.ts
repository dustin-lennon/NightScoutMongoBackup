import { Precondition } from '@sapphire/framework';
import { ChatInputCommandInteraction, Message } from 'discord.js';

export class GuildOnlyPrecondition extends Precondition {
	public override async chatInputRun(interaction: ChatInputCommandInteraction) {
		return interaction.guild
			? this.ok()
			: this.error({ message: '❌ This command can only be used in servers.' });
	}

	public override async messageRun(message: Message) {
		return message.guild
			? this.ok()
			: this.error({ message: '❌ This command can only be used in servers.' });
	}
}

declare module '@sapphire/framework' {
	interface Preconditions {
		GuildOnly: never;
	}
}
