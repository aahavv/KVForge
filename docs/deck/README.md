# Rebuilding the progress-review deck

`build_deck.js` generates `KVForge_Compiler_Design_Progress_Review_v3.pptx` with pptxgenjs.
It reads the figures in `results/figs/` and `results/figs_rtx4060/`.

```powershell
cd docs\deck
npm install pptxgenjs jszip
$env:NODE_PATH = "$PWD\node_modules"
node build_deck.js
```

The script refers to the pptx skill's `apply_theme.js` by absolute path near the top; adjust that
line if the skill is installed elsewhere. Close the output file in PowerPoint first, or the write fails.
