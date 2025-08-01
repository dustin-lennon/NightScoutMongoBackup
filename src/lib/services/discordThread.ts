import {
	ChannelType,
	TextChannel,
	ThreadChannel,
	EmbedBuilder,
	ActionRowBuilder,
	ButtonBuilder,
	ButtonStyle
} from 'discord.js';
import { container } from '@sapphire/framework';
import { envParseString } from '@skyra/env-utilities';

export interface ThreadCreationResult {
	success: boolean;
	thread?: ThreadChannel;
	threadId?: string;
	error?: string;
}

export interface ThreadMessageResult {
	success: boolean;
	messageId?: string;
	error?: string;
}

export class DiscordThreadService {
	private readonly channelId: string;

	constructor() {
		this.channelId = envParseString('BACKUP_CHANNEL_ID', '');
	}

	async createBackupThread(backupId: string): Promise<ThreadCreationResult> {
		try {
			if (!this.channelId) {
				throw new Error('BACKUP_CHANNEL_ID environment variable not set');
			}

			const channel = await container.client.channels.fetch(this.channelId) as TextChannel;
			if (!channel || channel.type !== ChannelType.GuildText) {
				throw new Error('Invalid backup channel or channel not found');
			}

			const threadName = `🗄️ Backup ${backupId}`;
			const thread = await channel.threads.create({
				name: threadName,
				autoArchiveDuration: 1440, // Archive after 1 day (in minutes)
				type: ChannelType.PublicThread,
				reason: 'Automated NightScout backup thread'
			});

			// Schedule thread deletion after 1 week
			this.scheduleThreadDeletion(thread.id);

			return {
				success: true,
				thread,
				threadId: thread.id
			};
		} catch (error) {
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Unknown Discord thread error'
			};
		}
	}

	async sendBackupStartMessage(threadId: string, collections: string[]): Promise<ThreadMessageResult> {
		try {
			const thread = await container.client.channels.fetch(threadId) as ThreadChannel;
			if (!thread) {
				throw new Error('Thread not found');
			}

			const embed = new EmbedBuilder()
				.setColor('Yellow')
				.setTitle('🔄 Backup Started')
				.setDescription('NightScout MongoDB backup process has begun...')
				.addFields([
					{
						name: '📋 Collections',
						value: collections.join(', ') || 'All default collections',
						inline: false
					},
					{
						name: '⏰ Started At',
						value: `<t:${Math.floor(Date.now() / 1000)}:F>`,
						inline: true
					}
				])
				.setTimestamp();

			const message = await thread.send({ embeds: [embed] });

			return {
				success: true,
				messageId: message.id
			};
		} catch (error) {
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Failed to send start message'
			};
		}
	}

	async sendBackupProgressMessage(
		threadId: string,
		stage: string,
		details?: string
	): Promise<ThreadMessageResult> {
		try {
			const thread = await container.client.channels.fetch(threadId) as ThreadChannel;
			if (!thread) {
				throw new Error('Thread not found');
			}

			const embed = new EmbedBuilder()
				.setColor('Blue')
				.setTitle(`🔄 ${stage}`)
				.setDescription(details || 'Processing...')
				.setTimestamp();

			const message = await thread.send({ embeds: [embed] });

			return {
				success: true,
				messageId: message.id
			};
		} catch (error) {
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Failed to send progress message'
			};
		}
	}

	async sendBackupCompleteMessage(
		threadId: string,
		result: {
			collectionsProcessed: string[];
			totalDocuments: number;
			originalSize?: number;
			compressedSize?: number;
			compressionRatio?: string;
			s3Url?: string;
			duration: number;
		}
	): Promise<ThreadMessageResult> {
		try {
			const thread = await container.client.channels.fetch(threadId) as ThreadChannel;
			if (!thread) {
				throw new Error('Thread not found');
			}

			const embed = new EmbedBuilder()
				.setColor('Green')
				.setTitle('✅ Backup Completed Successfully')
				.setDescription('Your NightScout backup has been completed and uploaded to S3!')
				.addFields([
					{
						name: '📋 Collections Processed',
						value: result.collectionsProcessed.join(', '),
						inline: false
					},
					{
						name: '📄 Total Documents',
						value: result.totalDocuments.toLocaleString(),
						inline: true
					},
					{
						name: '⏱️ Duration',
						value: `${result.duration.toFixed(2)}s`,
						inline: true
					}
				])
				.setTimestamp();

			// Add compression info if available
			if (result.originalSize && result.compressedSize && result.compressionRatio) {
				embed.addFields([
					{
						name: '📦 Compression',
						value: `${this.formatBytes(result.originalSize)} → ${this.formatBytes(result.compressedSize)} (${result.compressionRatio} reduction)`,
						inline: false
					}
				]);
			}

			const components = [];
			if (result.s3Url) {
				const row = new ActionRowBuilder<ButtonBuilder>()
					.addComponents(
						new ButtonBuilder()
							.setLabel('📥 Download Backup')
							.setStyle(ButtonStyle.Link)
							.setURL(result.s3Url)
					);
				components.push(row);

				embed.addFields([
					{
						name: '🔗 Download Link',
						value: `[Click here to download](${result.s3Url})`,
						inline: false
					}
				]);
			}

			const messageOptions: any = { embeds: [embed] };
			if (components.length > 0) {
				messageOptions.components = components;
			}

			const message = await thread.send(messageOptions);

			return {
				success: true,
				messageId: message.id
			};
		} catch (error) {
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Failed to send completion message'
			};
		}
	}

	async sendBackupErrorMessage(threadId: string, error: string): Promise<ThreadMessageResult> {
		try {
			const thread = await container.client.channels.fetch(threadId) as ThreadChannel;
			if (!thread) {
				throw new Error('Thread not found');
			}

			const embed = new EmbedBuilder()
				.setColor('Red')
				.setTitle('❌ Backup Failed')
				.setDescription(`The backup process encountered an error: ${error}`)
				.addFields([
					{
						name: '⏰ Failed At',
						value: `<t:${Math.floor(Date.now() / 1000)}:F>`,
						inline: true
					}
				])
				.setTimestamp();

			const message = await thread.send({ embeds: [embed] });

			return {
				success: true,
				messageId: message.id
			};
		} catch (error) {
			return {
				success: false,
				error: error instanceof Error ? error.message : 'Failed to send error message'
			};
		}
	}

	private scheduleThreadDeletion(threadId: string): void {
		// Schedule thread deletion after 1 week (7 days)
		const deleteAfter = 7 * 24 * 60 * 60 * 1000; // 7 days in milliseconds

		setTimeout(async () => {
			try {
				const thread = await container.client.channels.fetch(threadId) as ThreadChannel;
				if (thread) {
					await thread.delete('Automated cleanup after 1 week');
				}
			} catch (error) {
				console.error(`Failed to delete thread ${threadId}:`, error);
			}
		}, deleteAfter);
	}

	private formatBytes(bytes: number): string {
		const units = ['B', 'KB', 'MB', 'GB'];
		let size = bytes;
		let unitIndex = 0;

		while (size >= 1024 && unitIndex < units.length - 1) {
			size /= 1024;
			unitIndex++;
		}

		return `${size.toFixed(2)} ${units[unitIndex]}`;
	}
}

export const discordThreadService = new DiscordThreadService();
