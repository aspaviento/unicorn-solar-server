export const content = {
  appName: 'Busy Light',
  emptyState: {
    label: 'Busy Light',
    description: 'Waiting for the first display status.',
  },
  sections: {
    statuses: 'Busy Light statuses',
    power: 'Power controls',
  },
  statuses: {
    available: {
      label: 'Available',
      description: 'Available for conversations or interruptions.',
      buttonDescription: 'Green',
    },
    busy: {
      label: 'Busy',
      description: 'Busy; avoid interruptions.',
      buttonDescription: 'Red',
    },
    away: {
      label: 'Away',
      description: 'Away or not immediately available.',
      buttonDescription: 'Yellow',
    },
    outOfOffice: {
      label: 'Out of office',
      description: 'Out of the office.',
      buttonDescription: 'Blue',
    },
    appearOffline: {
      label: 'Appear Offline',
      description: 'Shown as unavailable while staying signed in.',
      buttonDescription: 'Gray',
    },
    doNotDisturb: {
      label: 'Do not Disturb',
      description: 'Do not interrupt unless it is urgent.',
      buttonDescription: 'Purple',
    },
    rainbow: {
      label: 'Rainbow',
      description: 'Startup and display test animation.',
      buttonDescription: 'Startup',
    },
    on: {
      label: 'On',
      description: 'Display on with an automatic color.',
    },
    off: {
      label: 'Off',
      description: 'Display off.',
    },
  },
  actions: {
    resetOverride: 'Reset override',
  },
  navigation: {
    home: 'Panel',
    apiDocs: 'API docs',
  },
  docs: {
    title: 'Server API',
    description: 'HTTP endpoints available to inspect and control the Busy Light display.',
    methodLabel: 'Method',
    endpointLabel: 'Endpoint',
    descriptionLabel: 'Description',
    endpoints: [
      {
        methods: ['GET', 'POST'],
        endpoint: '/api/on',
        description: 'Turns the display on with a random color.',
      },
      {
        methods: ['GET', 'POST'],
        endpoint: '/api/off',
        description: 'Turns the display off.',
      },
      {
        methods: ['GET'],
        endpoint: '/api/status',
        description: 'Returns color, brightness, current status, display model, and CPU temperature when available.',
      },
      {
        methods: ['POST'],
        endpoint: '/api/switch',
        description: 'Applies an RGB color. Accepts red, green, blue, and optional brightness and speed values.',
      },
      {
        methods: ['POST'],
        endpoint: '/api/rainbow',
        description: 'Shows the rainbow animation. Accepts optional brightness and speed values.',
      },
      {
        methods: ['GET', 'POST'],
        endpoint: '/api/available',
        description: 'Sets the Available status in green and enables the manual override.',
      },
      {
        methods: ['GET', 'POST'],
        endpoint: '/api/busy',
        description: 'Sets the Busy status in red and enables the manual override.',
      },
      {
        methods: ['GET', 'POST'],
        endpoint: '/api/away',
        description: 'Sets the Away status in yellow and enables the manual override.',
      },
      {
        methods: ['GET', 'POST'],
        endpoint: '/api/out-of-office',
        description: 'Sets the Out of office status in blue and enables the manual override.',
      },
      {
        methods: ['GET', 'POST'],
        endpoint: '/api/appear-offline',
        description: 'Sets the Appear Offline status in gray and enables the manual override.',
      },
      {
        methods: ['GET', 'POST'],
        endpoint: '/api/do-not-disturb',
        description: 'Sets the Do not Disturb status in purple and enables the manual override.',
      },
      {
        methods: ['GET', 'POST'],
        endpoint: '/api/reset',
        description: 'Disables the manual override so /api/switch can apply changes again.',
      },
    ],
  },
};
