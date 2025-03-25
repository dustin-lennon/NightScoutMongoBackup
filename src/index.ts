import { SapphireClient, LogLevel } from '@sapphire/framework';
import { GatewayIntentBits } from 'discord.js';
import 'dotenv/config';

const client = new SapphireClient({
	intents: [GatewayIntentBits.Guilds],
	logger: { level: LogLevel.Info }
});

client.once('ready', () => {
	console.log(`✅ Bot is online as ${client.user?.tag}!`);
});

client.login(process.env.DISCORD_TOKEN).catch((error) => {
	console.error('❌ Failed to login:', error);
});
