<?php
if (! defined('ABSPATH')) { exit; }

/**
 * Minimal PMTiles v3 reader. Range-reads one PNG tile from a local .pmtiles file.
 * Handles gzip-compressed two-level directories (root -> leaf -> tile) and the Hilbert tile id.
 * Tiles are stored uncompressed (tile_compression=none), so there is no per-tile inflate.
 */
class Permatiles_PMTiles_Reader {

    private $path;
    private $header = null;

    public function __construct($path) {
        $this->path = $path;
    }

    /** Hilbert tile id — ported byte-exact from pmtiles.tile.zxy_to_tileid. */
    public static function zxy_to_tileid($z, $x, $y) {
        $acc = intdiv((1 << ($z * 2)) - 1, 3);
        for ($a = $z - 1; $a >= 0; $a--) {
            $s = 1 << $a;
            $rx = $s & $x;
            $ry = $s & $y;
            $acc += ((3 * $rx) ^ $ry) << $a;
            if ($ry === 0) {                       // inlined rotate(n=s,...)
                if ($rx !== 0) { $x = $s - 1 - $x; $y = $s - 1 - $y; }
                $t = $x; $x = $y; $y = $t;
            }
        }
        return $acc;
    }

    private function read_at($offset, $length) {
        if ($length <= 0) { return ''; }
        $fh = @fopen($this->path, 'rb');
        if (! $fh) { return false; }
        if (fseek($fh, $offset) !== 0) { fclose($fh); return false; }
        $buf = '';
        while (strlen($buf) < $length && ! feof($fh)) {
            $chunk = fread($fh, $length - strlen($buf));
            if ($chunk === false) { fclose($fh); return false; }
            $buf .= $chunk;
        }
        fclose($fh);
        return $buf;
    }

    /** Parse and cache the 127-byte header. */
    public function header() {
        if ($this->header !== null) { return $this->header; }
        $b = $this->read_at(0, 127);
        if ($b === false || strlen($b) < 127 || substr($b, 0, 7) !== 'PMTiles' || ord($b[7]) !== 3) {
            return $this->header = false;
        }
        $u64 = function ($off) use ($b) {
            $lo = unpack('V', substr($b, $off, 4))[1];
            $hi = unpack('V', substr($b, $off + 4, 4))[1];
            return $lo + ($hi * 4294967296);
        };
        return $this->header = [
            'root_offset'           => $u64(8),
            'root_length'           => $u64(16),
            'leaf_offset'           => $u64(40),
            'leaf_length'           => $u64(48),
            'tile_data_offset'      => $u64(56),
            'tile_data_length'      => $u64(64),
            'internal_compression'  => ord($b[97]),  // 1=none 2=gzip
            'tile_compression'      => ord($b[98]),
            'tile_type'             => ord($b[99]),   // 2=PNG
            'min_zoom'              => ord($b[100]),
            'max_zoom'              => ord($b[101]),
        ];
    }

    /** Decompress (if gzip) and parse a directory blob into entries. */
    private function deserialize_directory($buf) {
        if ($buf === false) { return false; }
        if ($this->header['internal_compression'] === 2) {
            $buf = @gzdecode($buf);
            if ($buf === false) { return false; }
        }
        $pos = 0; $len = strlen($buf);
        $readv = function () use ($buf, &$pos, $len) {
            $shift = 0; $result = 0;
            while ($pos < $len) {
                $byte = ord($buf[$pos]); $pos++;
                $result |= ($byte & 0x7F) << $shift;
                if (($byte & 0x80) === 0) { break; }
                $shift += 7;
            }
            return $result;
        };
        $num = $readv();
        $ids = []; $rl = []; $lengths = []; $offsets = [];
        $last = 0;
        for ($i = 0; $i < $num; $i++) { $last += $readv(); $ids[$i] = $last; }
        for ($i = 0; $i < $num; $i++) { $rl[$i] = $readv(); }
        for ($i = 0; $i < $num; $i++) { $lengths[$i] = $readv(); }
        for ($i = 0; $i < $num; $i++) {
            $tmp = $readv();
            $offsets[$i] = ($i > 0 && $tmp === 0)
                ? $offsets[$i - 1] + $lengths[$i - 1]
                : $tmp - 1;
        }
        $entries = [];
        for ($i = 0; $i < $num; $i++) {
            $entries[] = ['tile_id' => $ids[$i], 'run_length' => $rl[$i],
                          'length' => $lengths[$i], 'offset' => $offsets[$i]];
        }
        return $entries;
    }

    /** Binary search — ported from pmtiles.tile.find_tile. */
    private function find_tile($entries, $tile_id) {
        $m = 0; $n = count($entries) - 1;
        while ($m <= $n) {
            $k = ($n + $m) >> 1;
            $c = $tile_id - $entries[$k]['tile_id'];
            if ($c > 0) { $m = $k + 1; }
            elseif ($c < 0) { $n = $k - 1; }
            else { return $entries[$k]; }
        }
        if ($n >= 0) {
            if ($entries[$n]['run_length'] === 0) { return $entries[$n]; }
            if ($tile_id - $entries[$n]['tile_id'] < $entries[$n]['run_length']) { return $entries[$n]; }
        }
        return null;
    }

    /** Return raw PNG bytes for z/x/y, or null if absent (pruned) / out of range. */
    public function get_tile($z, $x, $y) {
        $h = $this->header();
        if (! $h) { return null; }
        if ($z < $h['min_zoom'] || $z > $h['max_zoom']) { return null; }
        if ($x < 0 || $y < 0 || $x >= (1 << $z) || $y >= (1 << $z)) { return null; }
        $tile_id = self::zxy_to_tileid($z, $x, $y);
        $dir_offset = $h['root_offset'];
        $dir_length = $h['root_length'];
        for ($depth = 0; $depth < 4; $depth++) {
            $entries = $this->deserialize_directory($this->read_at($dir_offset, $dir_length));
            if (! $entries) { return null; }
            $entry = $this->find_tile($entries, $tile_id);
            if ($entry === null) { return null; }
            if ($entry['run_length'] === 0) {
                $dir_offset = $h['leaf_offset'] + $entry['offset'];
                $dir_length = $entry['length'];
                continue;
            }
            $data = $this->read_at($h['tile_data_offset'] + $entry['offset'], $entry['length']);
            return $data === false ? null : $data;
        }
        return null;
    }
}
