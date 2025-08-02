import { ApplyOptions, RequiresClientPermissions } from '@sapphire/decorators';
import { Command } from '@sapphire/framework';
import { EmbedBuilder, InteractionContextType, PermissionFlagsBits } from 'discord.js';
import { backupService } from '#lib/services/backup-simple';
import { DateTime } from 'luxon';

@ApplyOptions<Command.Options>({
	description: 'Perform a manual backup of the NightScout MongoDB database (simplified)',
	requiredUserPermissions: [PermissionFlagsBits.Administrator],
	preconditions: ['GuildOnly', 'BackupChannelOnly']
})
export class BackupSimpleCommand extends Command {
	public override registerApplicationCommands(registry: Command.Registry) {
		registry.registerChatInputCommand((builder) =>
			builder //
				.setName(this.name)
				.setDescription(this.description)
				.setContexts(InteractionContextType.Guild)
				.setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
				.addStringOption((option) =>
					option //
						.setName('collections')
						.setDescription('Comma-separated list of collections to backup (default: all)')
						.setRequired(false)
				)
		);
	}

	@RequiresClientPermissions(['EmbedLinks'])
	public override async chatInputRun(interaction: Command.ChatInputCommandInteraction) {
		await interaction.deferReply({ ephemeral: true });

		const embed = new EmbedBuilder();

		try {
			const collectionsParam = interaction.options.getString('collections');
			const collections = collectionsParam
				? collectionsParam.split(',').map(c => c.trim()).filter(c => c.length > 0)
				: undefined;

			// Start backup
			embed.setColor('Yellow')
				.setTitle('🔄 Backup in Progress')
				.setDescription('Starting manual backup of NightScout database...')
				.setTimestamp();

			await interaction.editReply({ embeds: [embed] });

			// Perform backup with thread creation
			const result = await backupService.performBackup({
				collections,
				createThread: true,
				isManual: true
			});

			if (result.success) {
				embed.setColor('Green')
					.setTitle('✅ Backup Completed Successfully')
					.setDescription('Manual backup has been completed!')
					.addFields([
						{
							name: '📚 Collections Processed',
							value: result.collectionsProcessed.join(', ') || 'None',
							inline: true
						},
						{
							name: '📄 Total Documents',
							value: result.totalDocumentsProcessed.toString(),
							inline: true
						},
						{
							name: '⏰ Backup Time',
							value: DateTime.fromJSDate(result.timestamp).toLocaleString(DateTime.DATETIME_FULL),
							inline: false
						}
					])
					.setTimestamp();

				// Add thread link if available
				if (result.threadId) {
					embed.addFields([
						{
							name: '💬 Discussion Thread',
							value: `<#${result.threadId}>`,
							inline: true
						}
					]);
				}

				await interaction.editReply({ embeds: [embed] });

				// Log successful backup
				this.container.logger.info(
					`[ManualBackup] Backup completed by ${interaction.user.tag}: ` +
					`${result.totalDocumentsProcessed} documents from ${result.collectionsProcessed.length} collections`
				);

			} else {
				embed.setColor('Red')
					.setTitle('❌ Backup Failed')
					.setDescription(`Backup failed with error: ${result.error}`)
					.addFields([
						{
							name: '📊 Partial Collections Processed',
							value: result.collectionsProcessed.length > 0
								? result.collectionsProcessed.join(', ')
								: 'None',
							inline: false
						}
					])
					.setTimestamp();

				await interaction.editReply({ embeds: [embed] });

				// Log failed backup
				this.container.logger.error(
					`[ManualBackup] Backup failed for ${interaction.user.tag}: ${result.error}`
				);
			}

		} catch (error) {
			const errorMessage = error instanceof Error ? error.message : String(error);

			embed.setColor('Red')
				.setTitle('❌ Backup Error')
				.setDescription(`An unexpected error occurred during backup: ${errorMessage}`)
				.setTimestamp();

			await interaction.editReply({ embeds: [embed] });

			// Log error
			this.container.logger.error(`[ManualBackup] Unexpected error for ${interaction.user.tag}:`, error);
		}
	}
}
