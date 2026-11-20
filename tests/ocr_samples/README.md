# OCR samples

Put ~30 photos of real ingredient labels here (jpg/png/webp), mixing Spanish and
English labels, good and bad lighting, curved packaging.

For each `foo.jpg` add `foo.txt` containing the ingredient list exactly as printed
(plain text, one line is fine).

Run:

    python3 scripts/ocr_benchmark.py tests/ocr_samples

Engines used when available: system `tesseract` (spa+eng), EasyOCR, Tesseract.js
(needs `npm install tesseract.js` in a local dir and `NODE_PATH` pointing to its
`node_modules`; not installed globally by the script). Each engine runs raw and
preprocessed (grayscale + autocontrast + 2x upscale). GO criteria per engine:
0 critical misses, verdict agreement >= 90%, avg time <= 5 s.
