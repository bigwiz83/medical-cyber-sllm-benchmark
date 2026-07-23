# Paper figures v3

`build_vector_art.mjs` reproduces all three publication SVG masters from the frozen figure source data. The visual system follows a clinical-journal data-graphic convention: white field, square geometry, thin black or gray rules, direct labels, one restrained teal accent, and grayscale comparators. Figure titles and interpretive prose remain in the manuscript captions rather than inside the artwork.

Release SVGs declare `Arial, Helvetica, sans-serif`; raster submission files are rendered on Windows with Arial installed. Displayed scores and confidence limits use two decimal places. Displayed P values use three decimal places, with values below 0.001 reported as `<0.001`. Machine-readable source data retain full numeric precision.

No Python plotting library is used. `masters/` contains the authoritative vector SVG sources. `submission/` contains 600-dpi PNG/TIFF and PDF derivatives generated from those masters. The files in `review/` are superseded historical prototypes and are not publication artifacts.
