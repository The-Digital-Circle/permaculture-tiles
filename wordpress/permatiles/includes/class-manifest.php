<?php
if (! defined('ABSPATH')) { exit; }

/** Loads manifest.json from the data dir and routes (z,x,y) to the owning PMTiles file. */
class Permatiles_Manifest {

    private $dir;
    private $data = null;

    public function __construct($dir) {
        $this->dir = rtrim($dir, '/');
    }

    public function exists() {
        return is_readable($this->dir . '/manifest.json');
    }

    private function data() {
        if ($this->data !== null) { return $this->data; }
        $raw = @file_get_contents($this->dir . '/manifest.json');
        $this->data = $raw ? json_decode($raw, true) : [];
        if (! is_array($this->data)) { $this->data = []; }
        return $this->data;
    }

    public function maxzoom() {
        return (int) ($this->data()['maxzoom'] ?? 0);
    }

    public function attribution() {
        return (string) ($this->data()['attribution'] ?? '');
    }

    public function ocean_tile_path() {
        $name = $this->data()['ocean_tile'] ?? 'ocean.png';
        return $this->dir . '/' . $name;
    }

    /**
     * Tile image format: 'png' or 'webp'. Absent means 'png' — that is the rollback path to any
     * release before v0.2.6, which shipped no tile_format key. Anything unrecognised also means
     * 'png': the value becomes a file extension, so it is never taken on trust.
     */
    public function tile_format() {
        $f = (string) ($this->data()['tile_format'] ?? 'png');
        return in_array($f, ['png', 'webp'], true) ? $f : 'png';
    }

    /** Absolute paths of every PMTiles file named in the manifest (the extraction source set). */
    public function tile_files() {
        $out = [];
        foreach ($this->data()['tiles'] ?? [] as $t) {
            if (! empty($t['file'])) { $out[] = $this->dir . '/' . $t['file']; }
        }
        return $out;
    }

    /** Absolute path to the PMTiles file that should hold (z,x,y), or null. */
    public function file_for($z, $x, $y) {
        foreach ($this->data()['tiles'] ?? [] as $t) {
            if ($z < $t['minzoom'] || $z > $t['maxzoom']) { continue; }
            $xr = $t['xrange'] ?? null;
            if (is_array($xr) && ($x < $xr[0] || $x > $xr[1])) { continue; }
            return $this->dir . '/' . $t['file'];
        }
        return null;
    }
}
