import { UserCommand } from "#commands/general/queryDb";
import { CommandInteraction, IntentsBitField } from "discord.js";
import { mockDeep } from "jest-mock-extended";
import { mongoService } from "#lib/services/mongo";
import { parseValidatedDate } from "#lib/util/date";
import { BucketScope, container, SapphireClient, LogLevel } from "@sapphire/framework";

jest.mock('#lib/services/mongo');
jest.mock('#lib/util/date');

// Mock the RequiresClientPermissions decorator
jest.mock('@sapphire/decorators', () => {
	const actual = jest.requireActual('@sapphire/decorators');
	return {
		...actual,
		RequiresClientPermissions: () => (_target: any, _propertyKey: string, descriptor: PropertyDescriptor) => {
			return descriptor;
		}
	};
});

describe('QueryDb UserCommand', () => {
	let command: UserCommand;

	// Initialize and mock the Sapphire client
	beforeAll(() => {
		// Create a real SapphireClient instance for tests
		const client = new SapphireClient({
			intents: new IntentsBitField().add(IntentsBitField.Flags.Guilds),
			logger: { level: LogLevel.Error } // Suppress logs during tests
		});

		// Attach the client to the container
		container.client = client;

		// Mock defaultCooldown properties
		container.client.options.defaultCooldown = {
			filteredCommands: [],
			limit: 1,        // Default to 1 entry
			delay: 0,        // No delay
			scope: BucketScope.User, // Default scope
			filteredUsers: [] // No filtered users
		};
	});

	// Tear down the client after all tests
	afterAll(async () => {
		await container.client.destroy();
	});

	beforeEach(() => {
		const mockContext = {
			name: "queryDb",
			path: __filename,
			root: process.cwd(),
			store: {
				userDirectory: process.cwd(),
				name: "commands",
				container,
				options: {
					enabled: true,
					preconditions: ['GuildOnly', 'BackupChannelOnly'],
					cooldownLimit: 0,
					cooldownDelay: 0,
					cooldownScope: BucketScope.User,
					cooldownFilteredUsers: [],
					runIn: null,
					requiredClientPermissions: undefined,
					requiredUserPermissions: undefined,
					nsfw: false
				}
			},
			location: {
				full: __filename,
				root: process.cwd(),
				relative: "src/commands/general/queryDb.ts",
				virtual: false,
				directories: ["src", "commands", "general"],
				name: "ping",
				toJSON: () => ({})
			}
		};

		command = new UserCommand(mockContext as any, {
			name: "queryDb",
			description: "Query MongoDB collections data",
			preconditions: ['GuildOnly', 'BackupChannelOnly'],
			enabled: true,
			cooldownLimit: 0,
			cooldownDelay: 0,
			cooldownScope: BucketScope.User,
			cooldownFilteredUsers: [],
			runIn: null,
			requiredClientPermissions: undefined,
			requiredUserPermissions: undefined,
			nsfw: false
		});
		jest.clearAllMocks();
	});

	const mockInteraction = () => {
		const interaction = mockDeep<CommandInteraction>();
		interaction.deferReply.mockResolvedValue({} as any);
		interaction.followUp.mockResolvedValue({} as any);
		interaction.editReply.mockResolvedValue({} as any);

		// Mock options methods
		interaction.options = {
			getString: jest.fn(),
			getInteger: jest.fn()
		} as any;

		// Mock the command type to be ChatInput
		(interaction as any).commandType = 1; // ApplicationCommandType.ChatInput

		// Mock guild and appPermissions for @RequiresClientPermissions
		(interaction as any).guild = {
			members: {
				me: {
					permissions: {
						missing: jest.fn().mockReturnValue([])
					}
				}
			}
		};

		(interaction as any).appPermissions = {
			missing: jest.fn().mockReturnValue([])
		};

		return interaction as any;
	};	const setupDateMock = (value: string | number) => {
		(parseValidatedDate as jest.Mock).mockReturnValue(value);
	};

	const mockMongoCollection = (docs: object[] = [{}], count = 1) => ({
		find: jest.fn().mockReturnValue({
			limit: jest.fn().mockReturnValue({
				toArray: jest.fn().mockResolvedValue(docs)
			})
		}),
		countDocuments: jest.fn().mockResolvedValue(count)
	});

	it('should be defined', () => {
		expect(command).toBeDefined();
		expect(command.name).toBe('querydb'); // Note: Sapphire converts to lowercase
		expect(command.description).toBe('Query MongoDB collections data');
	});

	it('should register application commands correctly', () => {
		const mockOption1 = {
			setName: jest.fn().mockReturnThis(),
			setDescription: jest.fn().mockReturnThis(),
			setChoices: jest.fn().mockReturnThis(),
			setRequired: jest.fn().mockReturnThis()
		};

		const mockOption2 = {
			setName: jest.fn().mockReturnThis(),
			setDescription: jest.fn().mockReturnThis(),
			setRequired: jest.fn().mockReturnThis()
		};

		let optionCallback1: any;

		const mockBuilder = {
			setName: jest.fn().mockReturnThis(),
			setDescription: jest.fn().mockReturnThis(),
			setContexts: jest.fn().mockReturnThis(),
			setDefaultMemberPermissions: jest.fn().mockReturnThis(),
			addStringOption: jest.fn().mockImplementation((callback) => {
				if (!optionCallback1) {
					optionCallback1 = callback;
					callback(mockOption1);
				} else {
					callback(mockOption2);
				}
				return mockBuilder;
			})
		};

		const mockRegisterChatInputCommand = jest.fn();
		const mockRegistry = {
			registerChatInputCommand: mockRegisterChatInputCommand.mockImplementation((callback) => {
				callback(mockBuilder);
				return mockBuilder;
			})
		};

		command.registerApplicationCommands(mockRegistry as any);

		expect(mockRegisterChatInputCommand).toHaveBeenCalled();
		expect(mockBuilder.setName).toHaveBeenCalledWith('querydb');
		expect(mockBuilder.setDescription).toHaveBeenCalledWith('Query MongoDB collections data');
		expect(mockBuilder.setContexts).toHaveBeenCalled();
		expect(mockBuilder.setDefaultMemberPermissions).toHaveBeenCalled();
		expect(mockBuilder.addStringOption).toHaveBeenCalledTimes(2);

		// Verify first option (collection)
		expect(mockOption1.setName).toHaveBeenCalledWith('collection');
		expect(mockOption1.setDescription).toHaveBeenCalledWith('What collection are you querying? (entries, devicestatus, treatments)');
		expect(mockOption1.setChoices).toHaveBeenCalled();
		expect(mockOption1.setRequired).toHaveBeenCalledWith(true);

		// Verify second option (date)
		expect(mockOption2.setName).toHaveBeenCalledWith('date');
		expect(mockOption2.setDescription).toHaveBeenCalledWith('From what date would you like to query? (YYYY-MM-DD)');
		expect(mockOption2.setRequired).toHaveBeenCalledWith(true);
	});

	it('should handle entries collection query successfully', async () => {
		const interaction = mockInteraction();
		const mockCollection = mockMongoCollection([{ _id: '123', date: 1640995200000, sgv: 120 }], 5);

		interaction.options.getString = jest.fn((option: string) => {
			if (option === 'collection') return 'entries';
			if (option === 'date') return '2022-01-01';
			return null;
		});

		setupDateMock(1640995200000); // Mock date parsing to return milliseconds

		(mongoService.getCollection as jest.Mock).mockResolvedValue(mockCollection);
		(mongoService.close as jest.Mock).mockResolvedValue(undefined);

		await command.chatInputRun(interaction);

		expect(interaction.deferReply).toHaveBeenCalled();
		expect(mongoService.getCollection).toHaveBeenCalledWith('entries');
		expect(interaction.followUp).toHaveBeenCalled();
		expect(mongoService.close).toHaveBeenCalled();
	});

	it('should handle devicestatus collection query successfully', async () => {
		const interaction = mockInteraction();
		const mockCollection = mockMongoCollection([{ _id: '456', created_at: '2022-01-01T00:00:00Z', uploader: { name: 'test' } }], 3);

		interaction.options.getString = jest.fn((option: string) => {
			if (option === 'collection') return 'devicestatus';
			if (option === 'date') return '2022-01-01';
			return null;
		});

		setupDateMock('2022-01-01T00:00:00Z'); // Mock date parsing to return ISO string

		(mongoService.getCollection as jest.Mock).mockResolvedValue(mockCollection);
		(mongoService.close as jest.Mock).mockResolvedValue(undefined);

		await command.chatInputRun(interaction);

		expect(interaction.deferReply).toHaveBeenCalled();
		expect(mongoService.getCollection).toHaveBeenCalledWith('devicestatus');
		expect(interaction.followUp).toHaveBeenCalled();
		expect(mongoService.close).toHaveBeenCalled();
	});	it('should handle treatments collection query successfully', async () => {
		const interaction = mockInteraction();
		const mockCollection = mockMongoCollection([{ _id: '789', timestamp: 1640995200000, eventTime: 'dinner' }], 2);

		interaction.options.getString = jest.fn((option: string) => {
			if (option === 'collection') return 'treatments';
			if (option === 'date') return '2022-01-01';
			return null;
		});

		setupDateMock(1640995200000); // Mock date parsing to return milliseconds

		(mongoService.getCollection as jest.Mock).mockResolvedValue(mockCollection);
		(mongoService.close as jest.Mock).mockResolvedValue(undefined);

		await command.chatInputRun(interaction);

		expect(interaction.deferReply).toHaveBeenCalled();
		expect(mongoService.getCollection).toHaveBeenCalledWith('treatments');
		expect(interaction.followUp).toHaveBeenCalled();
		expect(mongoService.close).toHaveBeenCalled();
	});

	it('should handle no results found', async () => {
		const interaction = mockInteraction();
		const mockCollection = mockMongoCollection([], 0);

		interaction.options.getString = jest.fn((option: string) => {
			if (option === 'collection') return 'entries';
			if (option === 'date') return '2022-01-01';
			return null;
		});

		setupDateMock(1640995200000);

		(mongoService.getCollection as jest.Mock).mockResolvedValue(mockCollection);
		(mongoService.close as jest.Mock).mockResolvedValue(undefined);

		await command.chatInputRun(interaction);

		expect(interaction.deferReply).toHaveBeenCalled();
		expect(interaction.editReply).toHaveBeenCalledWith('No entries found.');
		expect(mongoService.close).toHaveBeenCalled();
	});

	it('should handle no devicestatus results found', async () => {
		const interaction = mockInteraction();
		const mockCollection = mockMongoCollection([], 0);

		interaction.options.getString = jest.fn((option: string) => {
			if (option === 'collection') return 'devicestatus';
			if (option === 'date') return '2022-01-01';
			return null;
		});

		setupDateMock('2022-01-01T00:00:00Z');

		(mongoService.getCollection as jest.Mock).mockResolvedValue(mockCollection);
		(mongoService.close as jest.Mock).mockResolvedValue(undefined);

		await command.chatInputRun(interaction);

		expect(interaction.deferReply).toHaveBeenCalled();
		expect(interaction.editReply).toHaveBeenCalledWith('No device status found.');
		expect(mongoService.close).toHaveBeenCalled();
	});

	it('should handle no treatments results found', async () => {
		const interaction = mockInteraction();
		const mockCollection = mockMongoCollection([], 0);

		interaction.options.getString = jest.fn((option: string) => {
			if (option === 'collection') return 'treatments';
			if (option === 'date') return '2022-01-01';
			return null;
		});

		setupDateMock(1640995200000);

		(mongoService.getCollection as jest.Mock).mockResolvedValue(mockCollection);
		(mongoService.close as jest.Mock).mockResolvedValue(undefined);

		await command.chatInputRun(interaction);

		expect(interaction.deferReply).toHaveBeenCalled();
		expect(interaction.editReply).toHaveBeenCalledWith('No treatments found.');
		expect(mongoService.close).toHaveBeenCalled();
	});	it('should handle database errors gracefully', async () => {
		const interaction = mockInteraction();
		const error = new Error('Database connection failed');

		// Mock the logger to suppress console output during this test
		const loggerErrorSpy = jest.spyOn(container.logger, 'error').mockImplementation(() => {});

		interaction.options.getString = jest.fn((option: string) => {
			if (option === 'collection') return 'entries';
			if (option === 'date') return '2022-01-01';
			return null;
		});

		setupDateMock(1640995200000);

		(mongoService.getCollection as jest.Mock).mockRejectedValue(error);
		(mongoService.close as jest.Mock).mockResolvedValue(undefined);

		await command.chatInputRun(interaction);

		expect(interaction.deferReply).toHaveBeenCalled();
		expect(interaction.followUp).toHaveBeenCalledWith({
			embeds: expect.arrayContaining([
				expect.objectContaining({
					data: expect.objectContaining({
						color: expect.any(Number),
						description: expect.stringContaining('An error occurred while querying the database')
					})
				})
			])
		});
		expect(mongoService.close).toHaveBeenCalled();

		// Verify that the error was logged (even though we suppressed the output)
		expect(loggerErrorSpy).toHaveBeenCalledWith(error, '[MongoQueryError] Collection: entries | User: undefined');

		// Restore the original logger behavior
		loggerErrorSpy.mockRestore();
	});

	it('should handle unknown collection', async () => {
		const interaction = mockInteraction();

		interaction.options.getString = jest.fn((option: string) => {
			if (option === 'collection') return 'unknown';
			if (option === 'date') return '2022-01-01';
			return null;
		});

		(mongoService.getCollection as jest.Mock).mockResolvedValue({});
		(mongoService.close as jest.Mock).mockResolvedValue(undefined);

		await command.chatInputRun(interaction);

		expect(interaction.deferReply).toHaveBeenCalled();
		expect(interaction.editReply).toHaveBeenCalledWith('Unknown collection: unknown');
		expect(mongoService.close).toHaveBeenCalled();
	});

	it('should handle invalid date parsing', async () => {
		const interaction = mockInteraction();

		interaction.options.getString = jest.fn((option: string) => {
			if (option === 'collection') return 'entries';
			if (option === 'date') return 'invalid-date';
			return null;
		});

		// Mock parseValidatedDate to return undefined, but cast to avoid type error
		(parseValidatedDate as jest.Mock).mockReturnValue(undefined);

		(mongoService.getCollection as jest.Mock).mockResolvedValue({});
		(mongoService.close as jest.Mock).mockResolvedValue(undefined);

		await command.chatInputRun(interaction);

		expect(interaction.deferReply).toHaveBeenCalled();
		expect(parseValidatedDate).toHaveBeenCalledWith('invalid-date', interaction, 'millis');
		expect(mongoService.close).toHaveBeenCalled();
	});
});
