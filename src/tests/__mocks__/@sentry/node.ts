const SentryMock = {
	init: jest.fn(),
	captureException: jest.fn(),
	addBreadcrumb: jest.fn()
};

export = SentryMock;
