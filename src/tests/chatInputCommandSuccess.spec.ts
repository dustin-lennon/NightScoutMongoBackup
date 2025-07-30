import { UserListener } from "#listeners/commands/chatInputCommands/chatInputCommandSuccess";
import { container, SapphireClient, LogLevel } from "@sapphire/framework";
import { IntentsBitField } from "discord.js";
import { logSuccessCommand } from "#lib/utils";

// Mock the utils module
jest.mock('#lib/utils', () => ({
	logSuccessCommand: jest.fn()
}));

describe('ChatInputCommandSuccess Listener', () => {
	let listener: UserListener;

	beforeAll(() => {
		// Create a real SapphireClient instance for tests
		const client = new SapphireClient({
			intents: new IntentsBitField().add(IntentsBitField.Flags.Guilds),
			logger: { level: LogLevel.Debug } // Set to Debug to enable the listener
		});

		// Attach the client to the container
		container.client = client;
		container.logger = {
			level: LogLevel.Debug,
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
		const mockContext = {
			name: "chatInputCommandSuccess",
			path: __filename,
			root: process.cwd(),
			store: {
				userDirectory: process.cwd(),
				name: "listeners",
				container,
				options: {}
			},
			location: {
				full: __filename,
				root: process.cwd(),
				relative: "src/listeners/commands/chatInputCommands/chatInputCommandSuccess.ts",
				virtual: false,
				directories: ["src", "listeners", "commands", "chatInputCommands"],
				name: "chatInputCommandSuccess",
				toJSON: () => ({})
			}
		};

		listener = new UserListener(mockContext as any, {
			enabled: true,
			name: "chatInputCommandSuccess",
			event: "chatInputCommandSuccess"
		});

		jest.clearAllMocks();
	});

	describe('run', () => {
		it('should call logSuccessCommand with the payload', () => {
			const mockPayload = {
				interaction: {
					user: { username: 'testuser', id: '123456789' },
					guild: { name: 'Test Guild', id: '987654321', shardId: 0 }
				},
				command: { name: 'testCommand' },
				result: {}
			} as any;

			listener.run(mockPayload);

			expect(logSuccessCommand).toHaveBeenCalledWith(mockPayload);
		});
	});

	describe('onLoad', () => {
		it('should enable the listener when logger level is Debug or lower', () => {
			// Set container logger level to Debug
			(container.logger as any).level = LogLevel.Debug;

			const result = listener.onLoad();

			expect(listener.enabled).toBe(true);
			expect(result).toBeUndefined(); // super.onLoad() returns void for listeners
		});

		it('should disable the listener when logger level is higher than Debug', () => {
			// Set container logger level to Info (higher than Debug)
			(container.logger as any).level = LogLevel.Info;

			listener.onLoad();

			expect(listener.enabled).toBe(false);
		});

		it('should disable the listener when logger level is Error (much higher than Debug)', () => {
			// Set container logger level to Error
			(container.logger as any).level = LogLevel.Error;

			listener.onLoad();

			expect(listener.enabled).toBe(false);
		});

		it('should enable the listener when logger level is Trace (lower than Debug)', () => {
			// Set container logger level to Trace (lower than Debug)
			(container.logger as any).level = LogLevel.Trace;

			listener.onLoad();

			expect(listener.enabled).toBe(true);
		});
	});
});
