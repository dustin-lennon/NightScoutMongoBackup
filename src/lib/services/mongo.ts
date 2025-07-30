import { MongoClient, ServerApiVersion, Collection, Document } from 'mongodb';
import { envParseString } from '@skyra/env-utilities';
import { container } from '@sapphire/framework';

export class MongoService {
	private readonly client: MongoClient;
	private connected = false;

	constructor() {
		const uri =
			`mongodb+srv://${envParseString('MONGO_USERNAME')}:${envParseString('MONGO_PASSWORD')}` +
			`@${envParseString('MONGO_HOST')}/?retryWrites=true&w=majority`;

		this.client = new MongoClient(uri, {
			useBigInt64: true,
			serverApi: ServerApiVersion.v1
		});
	}

	async connectIfNeeded(): Promise<void> {
		if (!this.connected) {
			try {
				await this.client.connect();
				this.connected = true;
			} catch (error) {
				// Emit MongoDB connection error event
				container.client.emit('mongoConnectionError', error instanceof Error ? error : new Error('MongoDB connection failed'));
				throw error;
			}
		}
	}

	async getCollection<T extends Document = Document>(name: string): Promise<Collection<T>> {
		await this.connectIfNeeded();
		return this.client.db(envParseString('MONGO_DB')).collection<T>(name);
	}

	async close(): Promise<void> {
		if (this.connected) {
			await this.client.close();
			this.connected = false;
		}
	}
}

export const mongoService = process.env.NODE_ENV === 'test' ? {} as MongoService : new MongoService();
