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
