// A real code editor (CodeMirror 6) instead of a plain <textarea>. A raw
// textarea doesn't do anything useful with Tab (the browser just moves
// focus to the next control), has no C syntax highlighting, and has none
// of the bracket/indent affordances a student expects from an editor.
//
// Loaded lazily (only once a student opens an exercise) from esm.sh, with
// versions pinned to match what `npm install codemirror@6.0.1` actually
// resolves, so all the @codemirror/* sub-packages share one compatible
// dependency graph instead of esm.sh picking mismatched latest versions
// independently for each import.

const VERSIONS = {
  codemirror: "6.0.1",
  state: "6.7.1",
  view: "6.43.8",
  commands: "6.10.4",
  langCpp: "6.0.3",
};

let libPromise = null;

function loadLib() {
  if (!libPromise) {
    libPromise = Promise.all([
      import(`https://esm.sh/codemirror@${VERSIONS.codemirror}`),
      import(`https://esm.sh/@codemirror/state@${VERSIONS.state}`),
      import(`https://esm.sh/@codemirror/lang-cpp@${VERSIONS.langCpp}`),
      import(`https://esm.sh/@codemirror/commands@${VERSIONS.commands}`),
      import(`https://esm.sh/@codemirror/view@${VERSIONS.view}`),
    ]).then(([cm, state, langCpp, commands, view]) => ({
      EditorView: cm.EditorView,
      basicSetup: cm.basicSetup,
      EditorState: state.EditorState,
      cpp: langCpp.cpp,
      indentWithTab: commands.indentWithTab,
      keymap: view.keymap,
    }));
  }
  return libPromise;
}

let themeExtension = null;
function theme(EditorView) {
  if (!themeExtension) {
    themeExtension = EditorView.theme(
      {
        "&": { height: "100%", backgroundColor: "#010409", color: "#c9d1d9", fontSize: "0.9rem" },
        ".cm-scroller": { overflow: "auto", fontFamily: "Menlo, Consolas, 'DejaVu Sans Mono', monospace" },
        ".cm-content": { caretColor: "#58a6ff" },
        ".cm-gutters": { backgroundColor: "#010409", color: "#484f58", border: "none" },
        ".cm-activeLine": { backgroundColor: "#161b22aa" },
        ".cm-activeLineGutter": { backgroundColor: "#161b22aa" },
        "&.cm-focused .cm-cursor": { borderLeftColor: "#58a6ff" },
        "&.cm-focused .cm-selectionBackground, & ::selection": { backgroundColor: "#1f6feb44" },
      },
      { dark: true }
    );
  }
  return themeExtension;
}

export class CodeEditor {
  constructor() {
    this.view = null;
  }

  /** Mount (or remount) the editor into `container` with initial text `doc`. */
  async mount(container, { doc, onChange } = {}) {
    const lib = await loadLib();
    const { EditorView, basicSetup, EditorState, cpp, indentWithTab, keymap } = lib;

    this.destroy();

    this.view = new EditorView({
      state: EditorState.create({
        doc,
        extensions: [
          basicSetup,
          cpp(),
          keymap.of([indentWithTab]),
          theme(EditorView),
          EditorView.updateListener.of((update) => {
            if (update.docChanged && onChange) onChange(update.state.doc.toString());
          }),
        ],
      }),
      parent: container,
    });
  }

  getValue() {
    return this.view ? this.view.state.doc.toString() : "";
  }

  destroy() {
    if (this.view) {
      this.view.destroy();
      this.view = null;
    }
  }
}
