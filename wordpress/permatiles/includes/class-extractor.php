<?php
if (! defined('ABSPATH')) { exit; }

/**
 * Expands a PMTiles set into a STATIC tile pyramid ($dir/{z}/{x}/{y}.{ext}) that the web server serves
 * directly, with no PHP per request. This is what keeps the map from taking the site down: serving a
 * tile through WordPress boots the whole stack (~1.5s/tile) and a single map view fires dozens at once,
 * exhausting PHP-FPM. Static files are served by nginx in ~1ms with unbounded concurrency.
 *
 * Every position in 0..maxzoom is materialised: land tiles are written from the reader, and absent
 * (pruned open-ocean) positions are hard-linked to the shared ocean tile — because a MISSING file in
 * uploads/ still routes to WordPress (a slow 404), so we must never 404.
 */
class Permatiles_Extractor {

    /**
     * @param int      $maxzoom   inclusive top zoom to materialise
     * @param callable $resolve   fn($z,$x,$y) => raw encoded tile bytes, or null for open ocean
     * @param string   $ocean     path to the shared ocean tile (used for every absent position)
     * @param string   $tiles_dir destination root (wiped and rebuilt)
     * @param string   $ext       tile extension from the manifest ('png'|'webp')
     * @return array{tiles:int, ocean:int}
     */
    public static function extract($maxzoom, callable $resolve, $ocean, $tiles_dir, $ext = 'png') {
        self::rrmdir($tiles_dir);
        if (! wp_mkdir_p($tiles_dir)) { return ['tiles' => 0, 'ocean' => 0]; }
        $land = 0; $sea = 0;
        for ($z = 0; $z <= $maxzoom; $z++) {
            $n = 1 << $z;
            for ($x = 0; $x < $n; $x++) {
                $xdir = "$tiles_dir/$z/$x";
                wp_mkdir_p($xdir);
                for ($y = 0; $y < $n; $y++) {
                    $path = "$xdir/$y.$ext";
                    $tile = $resolve($z, $x, $y);
                    if ($tile !== null && $tile !== false && $tile !== '') {
                        file_put_contents($path, $tile);
                        $land++;
                    } else {
                        // hard-link the one ocean tile into every open-water position (copy fallback)
                        if (! @link($ocean, $path)) { @copy($ocean, $path); }
                        $sea++;
                    }
                }
            }
        }
        return ['tiles' => $land, 'ocean' => $sea];
    }

    /** Recursively remove a directory (used to rebuild the tree cleanly on each update). */
    public static function rrmdir($dir) {
        if (! is_dir($dir)) { return; }
        foreach (scandir($dir) as $e) {
            if ($e === '.' || $e === '..') { continue; }
            $p = "$dir/$e";
            is_dir($p) ? self::rrmdir($p) : @unlink($p);
        }
        @rmdir($dir);
    }

    /**
     * Build the resolver + run extraction for a pulled release living in $data_dir.
     * @return array{ok:bool, message?:string, tiles?:int, ocean?:int}
     *
     * Refuses (without touching the served tree) if a source PMTiles is missing — otherwise every
     * position would resolve to ocean and the map would go blank. Re-pull to restore the source.
     */
    public static function run($data_dir) {
        $manifest = new Permatiles_Manifest($data_dir);
        if (! $manifest->exists()) { return ['ok' => false, 'message' => 'no manifest']; }
        foreach ($manifest->tile_files() as $f) {
            if (! is_file($f)) {
                return ['ok' => false, 'message' => 'missing source ' . basename($f) . ' — re-pull to rebuild'];
            }
        }
        $readers = [];
        $resolve = function ($z, $x, $y) use ($manifest, &$readers) {
            $file = $manifest->file_for($z, $x, $y);
            if (! $file) { return null; }
            if (! isset($readers[$file])) { $readers[$file] = new Permatiles_PMTiles_Reader($file); }
            return $readers[$file]->get_tile($z, $x, $y);
        };
        $counts = self::extract((int) $manifest->maxzoom(), $resolve,
            $manifest->ocean_tile_path(), rtrim($data_dir, '/') . '/tiles',
            $manifest->tile_format());
        return ['ok' => true, 'tiles' => $counts['tiles'], 'ocean' => $counts['ocean']];
    }
}
