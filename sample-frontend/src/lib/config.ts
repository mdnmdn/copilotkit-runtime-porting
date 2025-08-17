export const appConfig = {
  copilot: {
    // Enable CopilotKit integration. When enabling, you must also provide either
    // a `runtimeUrl` (for self-hosted runtime) or a `publicApiKey`/`publicLicenseKey` for Copilot Cloud.
    enabled: true,
    // Example: "http://localhost:8000/api/chat" when backend is available
    runtimeUrl: "http://localhost:4000/copilotkit",
      // runtimeUrl: "http://localhost:8123/api/copilotkit",
    publicApiKey: undefined as string | undefined,
    publicLicenseKey: undefined as string | undefined,
    showDevConsole: true,
  },
} as const;

export type AppConfig = typeof appConfig;


