import {
	logSuccessCommand,
	getSuccessLoggerData
} from "../lib/utils";
import {
	Command,
	container,
	SapphireClient,
	LogLevel,
	BucketScope
} from "@sapphire/framework";
import { mockDeep } from "jest-mock-extended";
import { Guild, User, IntentsBitField } from "discord.js";

describe('Utils', () => {
	let mockCommand: Command;

	beforeAll(() => {
		// Create a real SapphireClient instance for tests
		const client = new SapphireClient({
			intents: new IntentsBitField().add(IntentsBitField.Flags.Guilds),
			logger: { level: LogLevel.Error }
		});

		// Attach the client to the container
		container.client = client;
		container.logger = {
			debug: jest.fn(),
			info: jest.fn(),
			warn: jest.fn(),
			error: jest.fn()
		} as any;
	});

	afterAll(async () => {
		await container.client.destroy();
	});

	beforeEach(() => {
		// Mock a command
		const mockContext = {
			name: "testCommand",
			path: __filename,
			root: process.cwd(),
			store: {
				userDirectory: process.cwd(),
				name: "commands",
				container,
				options: {
					enabled: true,
					preconditions: [],
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
				relative: "src/commands/test.ts",
				virtual: false,
				directories: ["src", "commands"],
				name: "test",
				toJSON: () => ({})
			}
		};

		mockCommand = new Command(mockContext as any, {
			name: "testCommand",
			description: "Test command",
			preconditions: [],
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

	describe('logSuccessCommand', () => {
		it('should log success for interaction-based payload', () => {
			const mockUser = mockDeep<User>();
			mockUser.username = 'testuser';
			mockUser.id = '123456789';

			const mockGuild = mockDeep<Guild>();
			mockGuild.name = 'Test Guild';
			mockGuild.id = '987654321';
			mockGuild.shardId = 0;

			const mockInteraction = {
				user: mockUser,
				guild: mockGuild
			};

			const payload = {
				interaction: mockInteraction,
				command: mockCommand,
				result: {}
			} as any;

			logSuccessCommand(payload);

			const logCall = (container.logger.debug as jest.Mock).mock.calls[0][0];
			expect(logCall).toContain('0'); // Just check for the number
			expect(logCall).toMatch(/testcommand/i);
			expect(logCall).toContain('testuser');
			expect(logCall).toContain('123456789');
			expect(logCall).toContain('Test Guild');
			expect(logCall).toContain('987654321');
		});

		it('should log success for message-based payload', () => {
			const mockUser = mockDeep<User>();
			mockUser.username = 'messageuser';
			mockUser.id = '111222333';

			const mockGuild = mockDeep<Guild>();
			mockGuild.name = 'Message Guild';
			mockGuild.id = '444555666';
			mockGuild.shardId = 1;

			const mockMessage = {
				author: mockUser,
				guild: mockGuild
			};

			const payload = {
				message: mockMessage,
				command: mockCommand,
				result: {}
			} as any;

			logSuccessCommand(payload);

			const logCall = (container.logger.debug as jest.Mock).mock.calls[0][0];
			expect(logCall).toContain('1'); // Just check for the number
			expect(logCall).toMatch(/testcommand/i);
			expect(logCall).toContain('messageuser');
			expect(logCall).toContain('111222333');
			expect(logCall).toContain('Message Guild');
			expect(logCall).toContain('444555666');
		});
	});

	describe('getSuccessLoggerData', () => {
		it('should return formatted logger data for guild command', () => {
			const mockUser = mockDeep<User>();
			mockUser.username = 'testuser';
			mockUser.id = '123456789';

			const mockGuild = mockDeep<Guild>();
			mockGuild.name = 'Test Guild';
			mockGuild.id = '987654321';
			mockGuild.shardId = 3;

			const result = getSuccessLoggerData(mockGuild, mockUser, mockCommand);

			expect(result.shard).toContain('3'); // Just check contains the number
			expect(result.commandName).toMatch(/testcommand/i);
			expect(result.author).toContain('testuser');
			expect(result.author).toContain('123456789');
			expect(result.sentAt).toContain('Test Guild');
			expect(result.sentAt).toContain('987654321');
		});

		it('should return formatted logger data for DM command (no guild)', () => {
			const mockUser = mockDeep<User>();
			mockUser.username = 'dmuser';
			mockUser.id = '555666777';

			const result = getSuccessLoggerData(null, mockUser, mockCommand);

			expect(result.shard).toContain('0'); // Default shard when guild is null
			expect(result.commandName).toMatch(/testcommand/i);
			expect(result.author).toContain('dmuser');
			expect(result.author).toContain('555666777');
			expect(result.sentAt).toBe('Direct Messages');
		});

		it('should handle guild with undefined shardId', () => {
			const mockUser = mockDeep<User>();
			mockUser.username = 'sharduser';
			mockUser.id = '444333222';

			const mockGuild = mockDeep<Guild>();
			mockGuild.name = 'No Shard Guild';
			mockGuild.id = '777888999';
			mockGuild.shardId = undefined as any;

			const result = getSuccessLoggerData(mockGuild, mockUser, mockCommand);

			expect(result.shard).toContain('0'); // Should default to 0 when shardId is undefined
		});
	});
});
