import { ApplyOptions, RequiresClientPermissions } from '@sapphire/decorators';
import { Command } from '@sapphire/framework';
import { DateTime } from 'luxon';
import { Collection, Document } from 'mongodb';
import {
	APIApplicationCommandOptionChoice,
	EmbedBuilder,
	InteractionContextType,
	PermissionFlagsBits,
	type APIEmbedField
} from 'discord.js';
import { parseValidatedDate } from '#lib/util/date';
import { mongoService } from '#lib/services/mongo';

@ApplyOptions<Command.Options>({
	description: 'Query MongoDB collections data',
	preconditions: ['GuildOnly', 'BackupChannelOnly']
})
export class UserCommand extends Command {
	readonly #collectionChoices: APIApplicationCommandOptionChoice<string>[] = [
		{ name: 'Entries', value: 'entries' },
		{ name: 'Device Status', value: 'devicestatus' },
		{ name: 'Treatments', value: 'treatments' },
	];

	public override registerApplicationCommands(registry: Command.Registry) {
		registry.registerChatInputCommand((builder) =>
			builder //
				.setName(this.name)
				.setDescription(this.description)
				.setContexts(InteractionContextType.Guild)
				.setDefaultMemberPermissions(PermissionFlagsBits.Administrator)
				.addStringOption((option) =>
					option //
						.setName('collection')
						.setDescription('What collection are you querying? (entries, devicestatus, treatments)')
						.setChoices(...this.#collectionChoices)
						.setRequired(true)
					)
				.addStringOption((option) =>
					option //
						.setName('date')
						.setDescription('From what date would you like to query? (YYYY-MM-DD)')
						.setRequired(true)
				)

		);
	}

	@RequiresClientPermissions(['EmbedLinks'])
	public override async chatInputRun(interaction: Command.ChatInputCommandInteraction) {
		await interaction.deferReply();

		// Establish the embed
		const embed = new EmbedBuilder();
		const dateParam = interaction.options.getString('date', true);
		const selectedCollection = interaction.options.getString('collection', true);

		// Time to query the database
		try {
			const collection = await mongoService.getCollection(selectedCollection);

			const handler = this.collectionHandlers[selectedCollection as keyof typeof this.collectionHandlers];
			if (!handler) {
				return interaction.editReply(`Unknown collection: ${selectedCollection}`);
			}

			return handler(interaction, collection, dateParam);
		} catch (error) {
			this.container.logger.error(error, `[MongoQueryError] Collection: ${selectedCollection} | User: ${interaction.user.tag}`);
			embed.setColor('Red');
			embed.setDescription(`❌ An error occurred while querying the database: ${error}`);
			return interaction.followUp({ embeds: [embed] });
		} finally {
			await mongoService.close();
		}
	}

	private flattenDocumentToFields(doc: Document): APIEmbedField[] {
		const fields: APIEmbedField[] = [];

		for (const key in doc) {
			if (key !== 'uploader') {
				fields.push({ name: key, value: `${doc[key]}` });
			} else {
				fields.push({ name: key, value: '\u200b', inline: false });

				for (const subKey in doc[key]) {
					fields.push({
						name: subKey,
						value: `${doc[key][subKey]}`,
						inline: true
					});
				}
			}
		}

		return fields;
	}

	private buildEmbed(
		collectionName: string,
		count: number,
		dateParam: string,
		fields: APIEmbedField[]
	): EmbedBuilder {
		const formattedDate = DateTime.fromFormat(dateParam, 'yyyy-LL-dd').toFormat('LLL dd yyyy');
		return new EmbedBuilder()
			.setTitle(`Oldest entry for ${collectionName} collection`)
			.setColor(0xffff00)
			.addFields(fields)
			.setFooter({
				text: `The ${collectionName} collection has ${count.toLocaleString()} entries since ${formattedDate}`
			});
	}

	private readonly collectionHandlers = {
		entries: this.handleEntries.bind(this),
		devicestatus: this.handleDeviceStatus.bind(this),
		treatments: this.handleTreatments.bind(this)
	};

	private async handleEntries(interaction: Command.ChatInputCommandInteraction, collection: Collection<Document>, dateParam: string) {
		// Date validation
		const date = parseValidatedDate(dateParam, interaction, 'millis');
		if (typeof date !== 'number') return;

		const query = { date: { $lte: date } };
		const result = await collection.find(query).limit(1).toArray();
		if (result.length === 0) return interaction.editReply('No entries found.');

		const fields = result.flatMap(this.flattenDocumentToFields);
		const count = await collection.countDocuments(query);
		const embed = this.buildEmbed('entries', count, dateParam, fields);

		return interaction.followUp({ embeds: [embed] });
	}

	private async handleDeviceStatus(interaction: Command.ChatInputCommandInteraction, collection: Collection<Document>, dateParam: string) {
		// ISO formatted date
		const dateToUTC = parseValidatedDate(dateParam, interaction, 'iso');
		if (typeof dateToUTC !== 'string') return;

		const query = { created_at: { $lte: dateToUTC } };
		const result = await collection.find(query).limit(1).toArray();
		if (result.length === 0) {
			return interaction.editReply('No device status found.');
		}

		const fields = result.flatMap(this.flattenDocumentToFields);
		const count = await collection.countDocuments(query);

		const finalEmbed = this.buildEmbed('devicestatus', count, dateParam, fields);

		return interaction.followUp({ embeds: [finalEmbed] });
	}

	private async handleTreatments(interaction: Command.ChatInputCommandInteraction, collection: Collection<Document>, dateParam: string) {
		// Date validation
		const date = parseValidatedDate(dateParam, interaction, 'millis');
		if (typeof date !== 'number') return;

		const query = { timestamp: { $lte: date } };
		const result = await collection.find(query).limit(1).toArray();
		if (result.length === 0) return interaction.editReply('No treatments found.');

		const fields = result.flatMap(this.flattenDocumentToFields);
		const count = await collection.countDocuments(query);
		const embed = this.buildEmbed('treatments', count, dateParam, fields);

		return interaction.followUp({ embeds: [embed] });
	}
}
