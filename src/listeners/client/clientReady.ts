import { Listener } from '@sapphire/framework';
import { Events, ActivityType } from 'discord.js';
import { ApplyOptions } from '@sapphire/decorators';

@ApplyOptions<Listener.Options>({
	event: Events.ClientReady,
	once: true
})
export class ClientReadyListener extends Listener {
	public run() {
		const { client } = this.container;
		this.container.logger.info(`✅ ${client.user?.tag} is ready and online!`);

		// Set bot activity status
		client.user?.setActivity('🗄️ Backing up NightScout data', {
			type: ActivityType.Watching
		});
	}
}
