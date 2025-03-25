import { LogLevel, SapphireClient } from '@sapphire/framework';
import { GatewayIntentBits } from 'discord.js';
import 'dotenv/config';

describe('Discord bot connection', () => {
	let client: SapphireClient;

	beforeAll(async () => {
		client = new SapphireClient({
			intents: [GatewayIntentBits.Guilds],
			logger: { level: LogLevel.None } // Disable internal logging if you don't want logs during tests
		});

		await client.login(process.env.DISCORD_TOKEN);
		await new Promise((resolve) => client.once('ready', resolve));
	});

	afterAll(async () => {
		await client.destroy();
	});

	it('should establish a successful connection', () => {
		expect(client.isReady()).toBeTruthy();
	});
});
