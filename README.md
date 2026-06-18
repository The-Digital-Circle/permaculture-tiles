# permaculture-tiles

Watercolour basemap tile generator for the perma.earth global map.

## Build

    make venv
    make download    # Natural Earth 10m -> data/
    make render      # -> build/tiles/ (PNG tree + ocean.png)
    make pack        # -> build/tiles/*.pmtiles + manifest.json

See docs in the perma map repo for the full design.
