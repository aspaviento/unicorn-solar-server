export const content = {
  appName: 'Unicorn Solar Server',
  navigation: {
    ariaLabel: 'Main navigation',
    home: 'Panel',
    apiDocs: 'API docs',
  },
  panel: {
    batteryAriaLabel: (percentage: number) => `Battery at ${percentage}%`,
    statusSummary: (flow: string, tariff: string, activeBars: number) =>
      `${flow} · ${tariff} tariff · ${activeBars} of 5 bars`,
    batterySection: 'Battery and energy flow',
    percentageLabel: (percentage: number) => `Percentage: ${percentage}%`,
    tariffSection: 'Electricity tariff',
    flows: {
      charging: 'Charging',
      discharging: 'Discharging',
      exporting: 'Exporting surplus',
    },
    tariffs: {
      low: 'Low',
      medium: 'Medium',
      high: 'High',
    },
  },
  docs: {
    title: 'Server API',
    description: 'HTTP endpoints available to update and inspect the solar battery display.',
    methodLabel: 'Method',
    endpointLabel: 'Endpoint',
    requestLabel: 'Request body',
    descriptionLabel: 'Description',
    endpoints: [
      {
        methods: ['POST'],
        endpoint: '/api/battery',
        request: '{"percentage": 65, "flow": "charging"}',
        description: 'Updates battery percentage and energy flow. Flow accepts charging, discharging, or exporting. Exporting requires 100%.',
      },
      {
        methods: ['POST'],
        endpoint: '/api/tariff',
        request: '{"level": "low"}',
        description: 'Updates the tariff terminal. Level accepts low, medium, or high.',
      },
      {
        methods: ['GET'],
        endpoint: '/api/status',
        request: 'None',
        description: 'Returns percentage, active bars, flow, tariff, display dimensions, rotation, hardware type, and last update information.',
      },
    ],
  },
};
