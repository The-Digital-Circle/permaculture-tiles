<?php
if (! defined('ABSPATH')) { exit; }

/**
 * Resolves a tile request to bytes + headers. Pure of WordPress: the rewrite rule, request parsing,
 * referer/rate-limit gating and output happen in permatiles.php, which calls resolve().
 */
class Permatiles_Tile_Endpoint {

    private $manifest;
    private $reader_factory;   // callable(string $file): object with get_tile($z,$x,$y)
    private $ocean_path;
    private $readers = [];

    public function __construct($manifest, callable $reader_factory, $ocean_path) {
        $this->manifest = $manifest;
        $this->reader_factory = $reader_factory;
        $this->ocean_path = $ocean_path;
    }

    private function reader($file) {
        if (! isset($this->readers[$file])) {
            $this->readers[$file] = call_user_func($this->reader_factory, $file);
        }
        return $this->readers[$file];
    }

    /**
     * @return array{status:int, content_type:string, body:?string, source:string}
     */
    public function resolve($z, $x, $y) {
        $z = (int) $z; $x = (int) $x; $y = (int) $y;
        if ($z < 0 || $z > $this->manifest->maxzoom()) {
            return ['status' => 404, 'content_type' => 'text/plain', 'body' => null, 'source' => 'none'];
        }
        $file = $this->manifest->file_for($z, $x, $y);
        $tile = $file ? $this->reader($file)->get_tile($z, $x, $y) : null;
        if ($tile !== null) {
            return ['status' => 200, 'content_type' => 'image/png', 'body' => $tile, 'source' => 'tile'];
        }
        // pruned / absent -> the single shared open-water tile
        $ocean = @file_get_contents($this->ocean_path);
        if ($ocean !== false) {
            return ['status' => 200, 'content_type' => 'image/png', 'body' => $ocean, 'source' => 'ocean'];
        }
        return ['status' => 404, 'content_type' => 'text/plain', 'body' => null, 'source' => 'none'];
    }
}
