"""Derive build_final_deck.js (final presentation) from build_deck.js (v3) plus snip_final.js."""
src = open("build_deck.js", encoding="utf-8").read()
snip = open("snip_final.js", encoding="utf-8").read()
base, rest = snip.split("// =================================================================== DEMO SLIDE")
demo, refs = rest.split("// =================================================================== REFERENCES")
demo = "// =================================================================== DEMO SLIDE" + demo
refs = "// =================================================================== REFERENCES" + refs

def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (old[:60], src.count(old))
    src = src.replace(old, new)

rep('const OUT = "C:/Users/aahav/Downloads/KVForge_Compiler_Design_Progress_Review_v3.pptx";',
    'const OUT = process.argv[2] || "C:/Users/aahav/Downloads/KVForge_Final_Presentation.pptx";')
rep('pres.title = "KVForge - Compiler Design Project Proposal";', 'pres.title = "KVForge - Compiler Design Final Presentation";')
rep('"COMPILER DESIGN  |  PROPOSAL AND PROGRESS REVIEW"', '"COMPILER DESIGN  |  FINAL PRESENTATION"')
rep('["Deck with real numbers", "33 slides, docs/results.md"]', '["Deck, live demo, guide", "final deck, demo scripts, 22-page guide"]')
rep("Read from abstracts and our knowledge of each paper; verify against full texts before the final submission. PersistentKV (June 2026) is the closest",
    "PersistentKV, our base paper, was read in full; the others from abstracts. PersistentKV (June 2026) is the closest")
rep("Prior art is judged from abstracts; full texts still to be checked.", "PersistentKV (the base paper) read in full; the others judged from abstracts.")
rep("The first two now have measurements behind them. The third is set up but not yet run.", "All three now have measurements behind them.")
rep("// =================================================================== 16. cost model equations", base + "\n// =================================================================== 16. cost model equations")
rep("// =================================================================== 19. plan", demo + "\n// =================================================================== 19. plan")
# replace the old two reference slides with the linked three
i = src.index("// =================================================================== 22-23. references")
j = src.index("(async () => {")
src = src[:i] + refs + "\n" + src[j:]
open("build_final_deck.js", "w", encoding="utf-8").write(src)
print("wrote build_final_deck.js")
