import * as Sentry from '@sentry/node';
import { CommandExecutedListener } from '../events/commandExecuted';
import { container, PreconditionContainerArray, Command } from '@sapphire/framework';
import { mockLogger } from './__mocks__/mockLogger';

describe('CommandExecutedListener', () => {
	const originalLogger = container.logger;

	beforeEach(() => {
		container.logger = mockLogger;
	});

	afterEach(() => {
		container.logger = originalLogger;
	});

	it('logs and adds a breadcrumb when a command is executed', () => {
		const listener = new CommandExecutedListener({} as any, { logger: mockLogger });

		jest.spyOn(Sentry, 'addBreadcrumb').mockImplementation(() => undefined);

		const mockCommand = {
			name: 'testCommand'
		};

		listener.run(mockCommand as any);

		expect(Sentry.addBreadcrumb).toHaveBeenCalledWith({
			category: 'commands',
			message: 'Executed testCommand',
			level: 'info'
		});
		expect(mockLogger.info).toHaveBeenCalledWith('Executed command: testCommand');
	});

	it('uses container.logger as fallback when no logger is provided', () => {
		container.logger = mockLogger; // <-- override directly

		const listener = new CommandExecutedListener({} as any); // no logger passed
		const mockPreconditions = new PreconditionContainerArray();
		const mockLocation = {
			root: '/mock/root',
			virtual: true,
			relative: 'relative/path',
			full: '/mock/root/relative/path',
			directories: ['mock', 'root', 'relative'],
			name: 'mockFile.ts',
			toJSON: () => ({
				root: '/mock/root',
				virtual: true,
				relative: 'relative/path',
				full: '/mock/root/relative/path',
				directories: ['mock', 'root', 'relative'],
				name: 'mockFile.ts'
			})
		};

		listener.run({
			name: 'testCommand',
			rawName: 'testCommand',
			description: 'Mock',
			location: mockLocation,
			preconditions: mockPreconditions,
			detailedDescription: '',
			registerApplicationCommands: () => Promise.resolve(),
			toJSON: () => ({
				name: 'testCommand',
				description: 'Mock command description',
				detailedDescription: '',
				category: 'mock',
				aliases: [],
				preconditions: [],
				options: {},
				enabled: true,
				location: {
					root: '/mock/root',
					virtual: true,
					relative: 'relative/path',
					full: '/mock/root/relative/path',
					directories: ['relative'],
					name: 'path',
					toJSON: () => ({
						root: '/mock/root',
						virtual: true,
						relative: 'relative/path',
						full: '/mock/root/relative/path',
						directories: ['relative'],
						name: 'path'
					})
				}
			})
		} as unknown as Command);

		expect(mockLogger.info).toHaveBeenCalledWith('Executed command: testCommand');
	});
});
