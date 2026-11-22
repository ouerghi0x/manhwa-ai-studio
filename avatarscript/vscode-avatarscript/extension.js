const vscode = require("vscode");
const cp = require("child_process");
const path = require("path");
const fs = require("fs");

let outputChannel = null;
let diagnosticCollection = null;
let statusBarPreviewItem = null;
let statusBarRenderItem = null;

/**
 * Locate the avatarscript CLI executable or Python interpreter automatically.
 */
function resolveAvatarScriptRunner(scriptPath) {
  const config = vscode.workspace.getConfiguration("avatarscript");
  const customExe = config.get("executablePath");
  if (customExe && fs.existsSync(customExe)) {
    return { exe: customExe, baseArgs: [] };
  }

  // Search upward from the .ava script path and across workspace folders for avatarscript/.venv
  const searchDirs = [];
  if (scriptPath) {
    let curr = path.dirname(scriptPath);
    for (let i = 0; i < 5; i++) {
      searchDirs.push(curr);
      searchDirs.push(path.join(curr, "avatarscript"));
      const parent = path.dirname(curr);
      if (parent === curr) break;
      curr = parent;
    }
  }

  if (vscode.workspace.workspaceFolders) {
    for (const folder of vscode.workspace.workspaceFolders) {
      const root = folder.uri.fsPath;
      searchDirs.push(root);
      searchDirs.push(path.join(root, "avatarscript"));
    }
  }

  const isWin = process.platform === "win32";
  const venvRelCandidates = isWin
    ? [
        path.join(".venv", "Scripts", "avatarscript.exe"),
        path.join(".venv", "Scripts", "python.exe"),
      ]
    : [
        path.join(".venv", "bin", "avatarscript"),
        path.join(".venv", "bin", "python"),
      ];

  for (const dir of searchDirs) {
    for (const rel of venvRelCandidates) {
      const candidate = path.join(dir, rel);
      if (fs.existsSync(candidate)) {
        if (candidate.toLowerCase().includes("python")) {
          return { exe: candidate, baseArgs: ["-m", "avatarscript.cli"] };
        }
        return { exe: candidate, baseArgs: [] };
      }
    }
  }

  return { exe: "avatarscript", baseArgs: [] };
}

/**
 * Parse compiler stderr and populate VS Code inline squiggly diagnostics.
 */
function updateDiagnosticsFromStderr(docUri, stderrText) {
  if (!diagnosticCollection || !docUri) return;
  if (!stderrText || !stderrText.trim()) {
    diagnosticCollection.delete(docUri);
    return;
  }

  const diagnostics = [];
  const lineRegex = /Line\s+(\d+),\s*Col\s+(\d+):\s*(.+)/g;
  let match;
  while ((match = lineRegex.exec(stderrText)) !== null) {
    const lineNum = Math.max(0, parseInt(match[1], 10) - 1);
    const colNum = Math.max(0, parseInt(match[2], 10) - 1);
    const msg = match[3].trim();
    const range = new vscode.Range(lineNum, colNum, lineNum, colNum + 20);
    diagnostics.push(
      new vscode.Diagnostic(range, msg, vscode.DiagnosticSeverity.Error)
    );
  }

  diagnosticCollection.set(docUri, diagnostics);
}

/**
 * Get the target .ava file path from a URI argument or active editor.
 */
async function getTargetAvaFile(uri) {
  if (uri && uri.fsPath && uri.fsPath.endsWith(".ava")) {
    const doc = vscode.workspace.textDocuments.find(
      (d) => d.uri.fsPath === uri.fsPath
    );
    if (doc && doc.isDirty) {
      await doc.save();
    }
    return uri;
  }

  const editor = vscode.window.activeTextEditor;
  if (!editor || !editor.document.fileName.endsWith(".ava")) {
    vscode.window.showWarningMessage(
      "Please open or select an AvatarScript (.ava) file first."
    );
    return null;
  }
  if (editor.document.isDirty) {
    await editor.document.save();
  }
  return editor.document.uri;
}

/**
 * Run an avatarscript CLI subcommand with progress notification, Output panel logs, and error squiggles.
 */
async function runAvatarCommand(subcommand, extraArgs, title, uri, showPanel = true) {
  const targetUri = await getTargetAvaFile(uri);
  if (!targetUri) return;

  const scriptPath = targetUri.fsPath;
  const runner = resolveAvatarScriptRunner(scriptPath);
  const fullArgs = [...runner.baseArgs, subcommand, scriptPath, ...extraArgs];
  const cwd = path.dirname(scriptPath);

  if (!outputChannel) {
    outputChannel = vscode.window.createOutputChannel("AvatarScript");
  }
  if (showPanel) {
    outputChannel.show(true);
  }
  outputChannel.appendLine(`\n========================================`);
  outputChannel.appendLine(`[AvatarScript] Running: "${runner.exe}" ${fullArgs.join(" ")}`);
  outputChannel.appendLine(`========================================`);

  return vscode.window.withProgress(
    {
      location: vscode.ProgressLocation.Notification,
      title: `AvatarScript: ${title} (${path.basename(scriptPath)})`,
      cancellable: true,
    },
    (progress, token) => {
      return new Promise((resolve) => {
        const child = cp.spawn(runner.exe, fullArgs, { cwd, shell: false });
        let stdoutBuf = "";
        let stderrBuf = "";

        token.onCancellationRequested(() => {
          child.kill();
          outputChannel.appendLine("[AvatarScript] Cancelled by user.");
          resolve();
        });

        child.stdout.on("data", (data) => {
          const text = data.toString();
          stdoutBuf += text;
          outputChannel.append(text);
        });

        child.stderr.on("data", (data) => {
          const text = data.toString();
          stderrBuf += text;
          outputChannel.append(text);
        });

        child.on("error", (err) => {
          outputChannel.appendLine(`[Error] Failed to launch avatarscript: ${err.message}`);
          vscode.window.showErrorMessage(`AvatarScript failed to start: ${err.message}`);
          resolve();
        });

        child.on("close", (code) => {
          if (code === 0) {
            if (diagnosticCollection) {
              diagnosticCollection.delete(targetUri);
            }
            if (subcommand === "validate") {
              vscode.window.showInformationMessage(
                `AvatarScript Valid: ${path.basename(scriptPath)}`
              );
            } else if (subcommand === "render") {
              vscode.window.showInformationMessage(
                `AvatarScript MP4 Rendered Successfully! (${path.basename(scriptPath)})`
              );
            } else if (subcommand === "export-frames") {
              vscode.window.showInformationMessage(
                `AvatarScript PNG Sequence Exported! (${path.basename(scriptPath)})`
              );
            }
          } else {
            updateDiagnosticsFromStderr(targetUri, stderrBuf);
            vscode.window.showErrorMessage(
              `AvatarScript ${subcommand} failed (see Output panel & Problems tab).`
            );
          }
          resolve();
        });
      });
    }
  );
}

function updateStatusBarVisibility() {
  const editor = vscode.window.activeTextEditor;
  const isAva = editor && editor.document.fileName.endsWith(".ava");
  if (statusBarPreviewItem && statusBarRenderItem) {
    if (isAva) {
      statusBarPreviewItem.show();
      statusBarRenderItem.show();
    } else {
      statusBarPreviewItem.hide();
      statusBarRenderItem.hide();
    }
  }
}

function activate(context) {
  outputChannel = vscode.window.createOutputChannel("AvatarScript");
  diagnosticCollection = vscode.languages.createDiagnosticCollection("avatarscript");
  context.subscriptions.push(outputChannel, diagnosticCollection);

  // Register Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("avatarscript.preview", (uri) =>
      runAvatarCommand("preview", [], "Live Preview", uri, false)
    ),
    vscode.commands.registerCommand("avatarscript.render", (uri) =>
      runAvatarCommand("render", [], "Rendering MP4 Video", uri, true)
    ),
    vscode.commands.registerCommand("avatarscript.validate", (uri) =>
      runAvatarCommand("validate", [], "Validating Script", uri, false)
    ),
    vscode.commands.registerCommand("avatarscript.exportFrames", async (uri) => {
      const targetUri = await getTargetAvaFile(uri);
      if (!targetUri) return;
      const baseName = path.basename(targetUri.fsPath, ".ava");
      const outDir = path.join(path.dirname(targetUri.fsPath), `${baseName}_frames`);
      return runAvatarCommand(
        "export-frames",
        ["-o", outDir],
        `Exporting RGBA PNGs -> ${baseName}_frames/`,
        targetUri,
        true
      );
    })
  );

  // Status Bar One-Click Buttons
  statusBarPreviewItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    100
  );
  statusBarPreviewItem.text = "$(play) Preview .ava";
  statusBarPreviewItem.tooltip = "Launch real-time Pygame preview for this .ava script (Ctrl+Shift+P -> AvatarScript: Preview)";
  statusBarPreviewItem.command = "avatarscript.preview";

  statusBarRenderItem = vscode.window.createStatusBarItem(
    vscode.StatusBarAlignment.Left,
    99
  );
  statusBarRenderItem.text = "$(device-camera-video) Render MP4";
  statusBarRenderItem.tooltip = "Render this .ava script directly to an H.264 MP4 video";
  statusBarRenderItem.command = "avatarscript.render";

  context.subscriptions.push(statusBarPreviewItem, statusBarRenderItem);
  context.subscriptions.push(
    vscode.window.onDidChangeActiveTextEditor(updateStatusBarVisibility)
  );
  updateStatusBarVisibility();

  // Auto-validate on save for immediate red squiggly line feedback
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument((doc) => {
      if (doc.fileName.endsWith(".ava")) {
        const runner = resolveAvatarScriptRunner(doc.fileName);
        const fullArgs = [...runner.baseArgs, "validate", doc.fileName];
        cp.execFile(
          runner.exe,
          fullArgs,
          { cwd: path.dirname(doc.fileName) },
          (err, stdout, stderr) => {
            if (err) {
              updateDiagnosticsFromStderr(doc.uri, stderr);
            } else {
              diagnosticCollection.delete(doc.uri);
            }
          }
        );
      }
    })
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
