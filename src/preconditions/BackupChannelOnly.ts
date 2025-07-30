import { Precondition } from '@sapphire/framework';
import { ChatInputCommandInteraction, Message } from 'discord.js';
import { envParseString } from '@skyra/env-utilities';

export class BackupChannelOnlyPrecondition extends Precondition {
	public override async chatInputRun(interaction: ChatInputCommandInteraction) {
		const backupChannelId = envParseString('BACKUP_CHANNEL_ID');

		// If no backup channel is configured, allow usage in any channel
		if (!backupChannelId) {
			return this.ok();
		}

		if (interaction.channelId !== backupChannelId) {
			return this.error({
				message: '❌ Backup commands can only be used in the designated backup channel.'
			});
		}

		return this.ok();
	}

	public override async messageRun(message: Message) {
		const backupChannelId = envParseString('BACKUP_CHANNEL_ID');

		// If no backup channel is configured, allow usage in any channel
		if (!backupChannelId) {
			return this.ok();
		}

		if (message.channelId !== backupChannelId) {
			return this.error({
				message: '❌ Backup commands can only be used in the designated backup channel.'
			});
		}

		return this.ok();
	}
}

declare module '@sapphire/framework' {
	interface Preconditions {
		BackupChannelOnly: never;
	}
}
