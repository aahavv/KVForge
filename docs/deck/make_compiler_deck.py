"""Derive build_compiler_deck.js (short, compiler-focused final deck) from the theme and
helpers of build_deck.js plus snip_compiler_deck.js.

    python make_compiler_deck.py
    node build_compiler_deck.js        (NODE_PATH must point at pptxgenjs / jszip)
"""
src = open("build_deck.js", encoding="utf-8").read()
head = src.split("// =================================================================== 1. title")[0]
old = 'const OUT = "C:/Users/aahav/Downloads/KVForge_Compiler_Design_Progress_Review_v3.pptx";'
assert head.count(old) == 1
head = head.replace(old, 'const OUT = process.argv[2] || "C:/Users/aahav/Downloads/KVForge_Final_Presentation.pptx";')
head = head.replace('pres.title = "KVForge - Compiler Design Project Proposal";', 'pres.title = "KVForge - Compiler Design Final Presentation";')
body = open("snip_compiler_deck.js", encoding="utf-8").read()
open("build_compiler_deck.js", "w", encoding="utf-8").write(head + body)
print("wrote build_compiler_deck.js")
