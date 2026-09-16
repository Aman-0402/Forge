import Editor, { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import EditorWorker from "monaco-editor/editor/editor.worker?worker";

// Use the bundled Monaco instead of fetching it from a CDN at runtime.
self.MonacoEnvironment = {
  getWorker: () => new EditorWorker(),
};
loader.config({ monaco });

monaco.editor.defineTheme("forge", {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "comment", foreground: "7b8494", fontStyle: "italic" },
    { token: "keyword", foreground: "d9a441" },
    { token: "string", foreground: "9fc59a" },
    { token: "number", foreground: "d69a6a" },
  ],
  colors: {
    "editor.background": "#18202e",
    "editor.lineHighlightBackground": "#1f2939",
    "editorLineNumber.foreground": "#4c5667",
    "editorCursor.foreground": "#d9a441",
    "editor.selectionBackground": "#274690aa",
  },
});

export default function CodeEditor({
  value,
  language,
  onChange,
  readOnly = false,
  height = "100%",
}: {
  value: string;
  language: string;
  onChange?: (value: string) => void;
  readOnly?: boolean;
  height?: string | number;
}) {
  return (
    <Editor
      height={height}
      theme="forge"
      language={language}
      value={value}
      onChange={(v) => onChange?.(v ?? "")}
      options={{
        readOnly,
        fontFamily: '"IBM Plex Mono", Consolas, monospace',
        fontSize: 14,
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        tabSize: 4,
        automaticLayout: true,
        padding: { top: 12 },
        renderLineHighlight: "line",
      }}
      loading={<div className="editor-loading">Loading editor…</div>}
    />
  );
}
