import { Precondition } from '@sapphire/framework';
import { ChatInputCommandInteraction, Message } from 'discord.js';
import { envParseString } from '@skyra/env-utilities';

export class BackupRateLimitPrecondition extends Precondition {
	private lastBackupTime = new Map<string, number>();

	public override async chatInputRun(interaction: ChatInputCommandInteraction) {
		return this.checkRateLimit(interaction.user.id);
	}

	public override async messageRun(message: Message) {
		return this.checkRateLimit(message.author.id);
	}

	private checkRateLimit(userId: string) {
		const rateLimitMinutes = parseInt(envParseString('BACKUP_RATE_LIMIT_MINUTES', '5'));
		const cooldownMs = rateLimitMinutes * 60 * 1000;
		const now = Date.now();
		const lastBackup = this.lastBackupTime.get(userId);

		if (lastBackup && (now - lastBackup) < cooldownMs) {
			const remainingTime = Math.ceil((cooldownMs - (now - lastBackup)) / 1000);
			const minutes = Math.floor(remainingTime / 60);
			const seconds = remainingTime % 60;

			const timeString = minutes > 0
				? `${minutes}m ${seconds}s`
				: `${seconds}s`;

			return this.error({
				message: `⏱️ Please wait ${timeString} before running another backup.`
			});
		}

		this.lastBackupTime.set(userId, now);
		return this.ok();
	}
}

declare module '@sapphire/framework' {
	interface Preconditions {
		BackupRateLimit: never;
	}
}
