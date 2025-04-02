import { CommandInteraction, IntentsBitField, SlashCommandBuilder } from 'discord.js';
import { container, BucketScope, SapphireClient, LogLevel } from '@sapphire/framework';
import { PingCommand } from '../commands/general/ping';

describe("PingCommand", () => {
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

	it("replies with Pong!", async () => {
		const mockReply = jest.fn();
		const interaction = {
			reply: mockReply,
		} as unknown as CommandInteraction;

		const mockContext = {
			name: "ping",
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
				relative: "src/commands/general/ping.ts",
				virtual: false,
				directories: ["src", "commands", "general"],
				name: "ping",
				toJSON: () => ({})
			}
		};

		const command = new PingCommand(mockContext as any, {
			name: "ping",
			description: "Ping the bot to check if it's alive.",
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

		await command.chatInputRun(interaction);
		expect(mockReply).toHaveBeenCalledWith("Pong!");
	});

	it("registers the chat input command with the correct name and description", () => {
		// Mock the CommandRegistry
		const mockRegisterChatInputCommand = jest.fn();
		const mockRegistry = {
			registerChatInputCommand: mockRegisterChatInputCommand
		};

		const mockContext = {
			name: "ping",
			path: __filename,
			root: process.cwd(),
			store: {
				userDirectory: process.cwd(),
				name: "commands",
				container,
			},
			location: {
				full: __filename,
				root: process.cwd(),
				relative: "src/commands/general/ping.ts",
				virtual: false,
				directories: ["src", "commands", "general"],
				name: "ping",
				toJSON: () => ({})
			}
		};

		const command = new PingCommand(mockContext as any, {
			name: "ping",
			description: "Ping the bot to check if it's alive.",
		});

		// Call registerApplicationCommands
		command.registerApplicationCommands(mockRegistry as any);

		// Validate that registerChatInputCommand was called
		expect(mockRegisterChatInputCommand).toHaveBeenCalledWith(expect.any(Function));

		// Use SlashCommandBuilder to simulate the builder's methods
		const mockBuilder = {
			setName: jest.fn().mockReturnThis(),
			setDescription: jest.fn().mockReturnThis()
		};

		// Extract the builder function and execute it with the mock builder
		const builderFunction = mockRegisterChatInputCommand.mock.calls[0][0];
		builderFunction(mockBuilder);

		// Validate that the builder methods were called with the correct arguments
		expect(mockBuilder.setName).toHaveBeenCalledWith("ping");
		expect(mockBuilder.setDescription).toHaveBeenCalledWith("Ping the bot to check if it's alive.");
	});

	it("creates a PingCommand instance with the correct properties", () => {
		const mockContext = {
			name: "ping",
			path: __filename,
			root: process.cwd(),
			store: {
				userDirectory: process.cwd(),
				name: "commands",
				container
			},
			location: {
				full: __filename,
				root: process.cwd(),
				relative: "src/commands/general/ping.ts",
				virtual: false,
				directories: ["src", "commands", "general"],
				name: "ping",
				toJSON: () => ({})
			}
		};

		const commandOptions = {
			name: "ping",
			description: "Ping the bot to check if it's alive.",
		};

		const command = new PingCommand(mockContext as any, commandOptions);

		// Validate the properties
		expect(command.name).toBe("ping");
		expect(command.description).toBe("Ping the bot to check if it's alive.");
	});

	it("directly validates constructor logic", () => {
		// Mock minimal context
		const mockContext = {
			name: "ping",
			path: __filename,
			root: process.cwd(),
			store: {
				userDirectory: process.cwd(),
				name: "commands",
				container: {},
			},
			location: {
				full: __filename,
				root: process.cwd(),
				relative: "src/commands/general/ping.ts",
				virtual: false,
				directories: ["src", "commands", "general"],
				name: "ping",
				toJSON: () => ({}),
			},
		} as Command.LoaderContext;

		const commandOptions = {
			name: "ping",
			description: "Ping the bot to check if it's alive.",
		};

		// Spy on the constructor logic (forces explicit tracking)
		const constructorSpy = jest.fn();
		const CustomPingCommand = class extends PingCommand {
			public constructor(context: Command.LoaderContext, options: Command.Options) {
				constructorSpy();
				super(context, options);
			}
		};

		const command = new CustomPingCommand(mockContext, commandOptions);

		// Assertions
		expect(constructorSpy).toHaveBeenCalledTimes(1);
		expect(command.name).toBe("ping");
		expect(command.description).toBe("Ping the bot to check if it's alive.");
	});

});
