const { workspace, window } = require("vscode");
const { LanguageClient, TransportKind } = require("vscode-languageclient/node");

let client;

function activate(context) {
  const config = workspace.getConfiguration("bddframe");
  const python = config.get("pythonPath", "python3");
  const severity = config.get("unknownStepSeverity", "warning");

  const serverOptions = {
    command: python,
    args: ["-m", "bddframe.lsp.server"],
    transport: TransportKind.stdio,
    options: {
      env: { ...process.env, BDDFRAME_UNKNOWN_STEP_SEVERITY: severity },
    },
  };

  const clientOptions = {
    // activate for .feature files registered as bddframe language
    documentSelector: [{ scheme: "file", language: "bddframe" }],
    synchronize: {
      // re-validate when .env changes (variable completions update)
      fileEvents: workspace.createFileSystemWatcher("**/.env"),
    },
  };

  client = new LanguageClient(
    "bddframe-lsp",
    "BDDFrame Language Server",
    serverOptions,
    clientOptions
  );

  client.start().catch((err) => {
    window.showErrorMessage(
      `BDDFrame LSP failed to start: ${err.message}\n` +
      `Make sure bddframe is installed: pip install bddframe[lsp]`
    );
  });
}

function deactivate() {
  if (client) return client.stop();
}

module.exports = { activate, deactivate };
