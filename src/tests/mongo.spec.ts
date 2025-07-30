import { MongoService } from "#lib/services/mongo";
import { MongoClient, Collection } from 'mongodb';
import { envParseString } from '@skyra/env-utilities';

// Mock the container
jest.mock('@sapphire/framework', () => ({
  ...jest.requireActual('@sapphire/framework'),
  container: {
    client: {
      emit: jest.fn()
    }
  }
}));

// Mock the external dependencies
jest.mock('mongodb');
jest.mock('@skyra/env-utilities');

describe('MongoService', () => {
	let mongoService: MongoService;
	let mockClient: jest.Mocked<MongoClient>;
	let mockDb: any;
	let mockCollection: jest.Mocked<Collection>;

	beforeEach(() => {
		// Mock environment variables
		(envParseString as jest.Mock).mockImplementation((key: string) => {
			switch (key) {
				case 'MONGO_USERNAME': return 'testuser';
				case 'MONGO_PASSWORD': return 'testpass';
				case 'MONGO_HOST': return 'cluster0.test.mongodb.net';
				case 'MONGO_DB': return 'testdb';
				default: return 'default';
			}
		});

		// Mock MongoDB client and database
		mockCollection = {
			find: jest.fn(),
			insertOne: jest.fn(),
			updateOne: jest.fn(),
			deleteOne: jest.fn(),
			countDocuments: jest.fn()
		} as any;

		mockDb = {
			collection: jest.fn().mockReturnValue(mockCollection)
		};

		mockClient = {
			connect: jest.fn().mockResolvedValue(undefined),
			close: jest.fn().mockResolvedValue(undefined),
			db: jest.fn().mockReturnValue(mockDb)
		} as any;

		(MongoClient as jest.MockedClass<typeof MongoClient>).mockImplementation(() => mockClient);

		mongoService = new MongoService();
		jest.clearAllMocks();
	});

	describe('constructor', () => {
		it('should create MongoClient with correct connection string and options', () => {
			// Create a new instance to test constructor
			new MongoService();

			expect(MongoClient).toHaveBeenCalledWith(
				'mongodb+srv://testuser:testpass@cluster0.test.mongodb.net/?retryWrites=true&w=majority',
				{
					useBigInt64: true,
					serverApi: "1"
				}
			);
		});
	});

	describe('connectIfNeeded', () => {
		it('should connect when not already connected', async () => {
			await mongoService.connectIfNeeded();

			expect(mockClient.connect).toHaveBeenCalledTimes(1);
		});

		it('should not connect again when already connected', async () => {
			// First connection
			await mongoService.connectIfNeeded();
			expect(mockClient.connect).toHaveBeenCalledTimes(1);

			// Second call should not connect again
			await mongoService.connectIfNeeded();
			expect(mockClient.connect).toHaveBeenCalledTimes(1);
		});

		it('should handle connection errors', async () => {
			const error = new Error('Connection failed');
			mockClient.connect.mockRejectedValueOnce(error);

			await expect(mongoService.connectIfNeeded()).rejects.toThrow('Connection failed');
		});
	});

	describe('getCollection', () => {
		it('should connect and return collection', async () => {
			const collection = await mongoService.getCollection('testCollection');

			expect(mockClient.connect).toHaveBeenCalledTimes(1);
			expect(mockClient.db).toHaveBeenCalledWith('testdb');
			expect(mockDb.collection).toHaveBeenCalledWith('testCollection');
			expect(collection).toBe(mockCollection);
		});

		it('should not connect again if already connected', async () => {
			// First call
			await mongoService.getCollection('collection1');
			expect(mockClient.connect).toHaveBeenCalledTimes(1);

			// Second call should not connect again
			await mongoService.getCollection('collection2');
			expect(mockClient.connect).toHaveBeenCalledTimes(1);
			expect(mockDb.collection).toHaveBeenCalledWith('collection2');
		});

		it('should handle different collection names', async () => {
			await mongoService.getCollection('entries');
			expect(mockDb.collection).toHaveBeenCalledWith('entries');

			await mongoService.getCollection('devicestatus');
			expect(mockDb.collection).toHaveBeenCalledWith('devicestatus');

			await mongoService.getCollection('treatments');
			expect(mockDb.collection).toHaveBeenCalledWith('treatments');
		});
	});

	describe('close', () => {
		it('should close connection when connected', async () => {
			// First connect
			await mongoService.connectIfNeeded();
			expect(mockClient.connect).toHaveBeenCalledTimes(1);

			// Then close
			await mongoService.close();
			expect(mockClient.close).toHaveBeenCalledTimes(1);
		});

		it('should not close when not connected', async () => {
			// Close without connecting first
			await mongoService.close();
			expect(mockClient.close).not.toHaveBeenCalled();
		});

		it('should allow reconnection after closing', async () => {
			// Connect, close, then connect again
			await mongoService.connectIfNeeded();
			await mongoService.close();
			await mongoService.connectIfNeeded();

			expect(mockClient.connect).toHaveBeenCalledTimes(2);
			expect(mockClient.close).toHaveBeenCalledTimes(1);
		});

		it('should handle close errors', async () => {
			// Connect first
			await mongoService.connectIfNeeded();

			const error = new Error('Close failed');
			mockClient.close.mockRejectedValueOnce(error);

			await expect(mongoService.close()).rejects.toThrow('Close failed');
		});
	});
});
