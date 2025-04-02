import { Command } from "@sapphire/framework";
import type { CommandInteraction } from "discord.js";

export class PingCommand extends Command {
	public constructor(context: Command.LoaderContext, options: Command.Options = {}) {
		super(context, {
			...options,
			name: "ping",
			description: "Ping the bot to check if it's alive.",
		});
	}

	public override registerApplicationCommands(registry: Command.Registry) {
		registry.registerChatInputCommand(
			(builder) =>
				builder //
					.setName(this.name)
					.setDescription(this.description)
		);
	}

	public override async chatInputRun(interaction: CommandInteraction) {
		await interaction.reply('Pong!');
	}
}
