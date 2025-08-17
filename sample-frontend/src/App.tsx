import { useMemo } from "react";
import reactLogo from "./assets/react.svg";
import viteLogo from "/vite.svg";
import { CopilotSidebar } from "@copilotkit/react-ui";
import "@copilotkit/react-ui/styles.css";
import { appConfig } from "@/lib/config";

function App() {
  const labels = useMemo(
    () => ({
      title: "Your Assistant",
      initial: "Hi! 👋 How can I assist you today?",
      placeholder: "Type a message...",
    }),
    [],
  );

  const copilotActive = Boolean(
    appConfig.copilot.enabled &&
      (appConfig.copilot.runtimeUrl || appConfig.copilot.publicApiKey || appConfig.copilot.publicLicenseKey),
  );

  const Content = (
    <div className="p-6 space-y-6">
      <div className="flex items-center gap-4">
        <a href="https://vite.dev" target="_blank" rel="noreferrer">
          <img src={viteLogo} className="h-10 w-10" alt="Vite logo" />
        </a>
        <a href="https://react.dev" target="_blank" rel="noreferrer">
          <img src={reactLogo} className="h-10 w-10" alt="React logo" />
        </a>
        <h1 className="text-2xl font-semibold">Vite + React</h1>
      </div>

      <div className="text-sm text-muted-foreground">
        {copilotActive
          ? 'Use the button on the right to open the Copilot sidebar, or press "/".'
          : 'Copilot is disabled or not configured. Update src/lib/config.ts to enable.'}
      </div>
    </div>
  );

  return copilotActive ? (
    <CopilotSidebar labels={labels} defaultOpen>
      {Content}
    </CopilotSidebar>
  ) : (
    Content
  );
}

export default App;
