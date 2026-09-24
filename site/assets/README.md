# Hero artwork

`station-traces.svg` is original, locally generated vector artwork from the project's saved observed PM2.5 targets. No photograph, stock asset, remote image or generated raster image is used.

Source data: Song Chen (2017), [UCI Beijing Multi-Site Air Quality](https://doi.org/10.24432/C5RK5G), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The derived SVG is also offered under CC BY 4.0; credit “StationShift, derived from Song Chen / UCI Beijing Multi-Site Air Quality.” Attribution is embedded in the SVG.

Rebuild with `python scripts/build_site.py`. The builder reads observed targets from each station's saved 30d/+24h Chronos configuration; these observations are identical across supported configurations. Timestamp positions and a shared concentration scale are preserved. Traces are vertically offset and filled for an abstract landscape composition. They are sampled test targets, not a continuous hourly record or geographic map. Station names appear in SVG title elements. The graphic makes no comparison of model performance.
