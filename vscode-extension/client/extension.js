const { workspace, window } = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function activate(context) {
  const config = workspace.getConfiguration("noodle");
  const python = config.get("pythonPath", "python3");
  const severity = config.get("unknownStepSeverity", "warning");

  const serverOptions = {
    command: python,
    args: ["-m", "noodle.lsp.server"],
    transport: TransportKind.stdio,
    options: {
      env: { ...process.env, NOODLE_UNKNOWN_STEP_SEVERITY: severity },
    },
  };

  const clientOptions = {
    // activate for .feature files registered as noodle language
    documentSelector: [{ scheme: "file", language: "noodle" }],
    synchronize: {
      // re-validate when .env changes (variable completions update)
      fileEvents: workspace.createFileSystemWatcher("**/.env"),
    },
  };

  client = new LanguageClient(
    "noodle-lsp",
    "Noodle Language Server",
    serverOptions,
    clientOptions
  );

  client.start().catch((err) => {
    window.showErrorMessage(
      `Noodle LSP failed to start: ${err.message}\n` +
      `Make sure noodle is installed: pip install noodle[lsp]`
    );
  });
}

function deactivate() {
  if (client) return client.stop();
}

module.exports = { activate, deactivate };
