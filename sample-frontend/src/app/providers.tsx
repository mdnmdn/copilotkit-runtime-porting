import type { ReactNode } from "react";
import { ThemeProvider } from "./theme-provider.tsx";
import { appConfig } from "@/lib/config";
import { CopilotKit } from "@copilotkit/react-core";

interface AppProvidersProps {
  children: ReactNode;
}

function NoopProvider({ children }: { children: ReactNode }): ReactNode {
  return children;
}

export function AppProviders({ children }: AppProvidersProps) {
  const { enabled, runtimeUrl, publicApiKey, publicLicenseKey, showDevConsole } = appConfig.copilot;
  const hasValidConfig = Boolean(runtimeUrl || publicApiKey || publicLicenseKey);

  const Provider = enabled && hasValidConfig
    ? ({ children }: { children: ReactNode }) => (
      <CopilotKit
        runtimeUrl={runtimeUrl}
        publicApiKey={publicApiKey}
        publicLicenseKey={publicLicenseKey}
        showDevConsole={showDevConsole}
        agent="Chef"
      >
        {children}
      </CopilotKit>
    )
    : NoopProvider;

  return (
    <ThemeProvider>
      <Provider>{children}</Provider>
    </ThemeProvider>
  );
}


