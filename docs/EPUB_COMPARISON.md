# EPUB feature comparison

## Scope and priorities

Compare executed stock Xteink reading behavior with CrossPoint using the same generated EPUB fixtures and scripted actions. CrossInk has already been evaluated separately and is excluded here.

Use QEMU as the working backend for now. It completed the UI sequences faster in the initial experiments. Replace missing SD transport as necessary, while preserving the firmware's filesystem/EPUB/rendering logic. Full peripheral accuracy and CrossPoint performance benchmarking are deferred.

## Current evidence

Home navigation and Settings work with diagnostic GPIO/ADC responses. The initial Select-on-Read probe returned to Home and did not open a book. No EPUB comparison has been completed yet.

## First reading fixtures

Use synthetic, reproducible EPUBs with known contents to examine:

- chapter navigation and table of contents;
- text styling, spacing, alignment and indentation;
- embedded images and image sizing;
- internal links and footnotes;
- reading settings, pagination, progress and reopen behavior.

Record observed output and limits before choosing any CrossPoint implementation. An inability to reach a feature because of the adapter is not a firmware limitation.
