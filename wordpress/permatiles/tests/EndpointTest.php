<?php
use PHPUnit\Framework\TestCase;

class EndpointTest extends TestCase {
    private function endpoint() {
        $manifest = new Permatiles_Manifest(__DIR__ . '/fixtures');   // routes z0-6 -> file A
        // reader factory returns a fake reader keyed by file
        $factory = function ($file) {
            return new class($file) {
                public $file;
                public function __construct($f) { $this->file = $f; }
                public function get_tile($z, $x, $y) {
                    return ($z === 3 && $x === 1 && $y === 1) ? 'PNGDATA' : null;
                }
            };
        };
        return new Permatiles_Tile_Endpoint($manifest, $factory, __DIR__ . '/fixtures/ocean.png');
    }

    public function test_serves_known_tile() {
        $r = $this->endpoint()->resolve(3, 1, 1);
        $this->assertSame('PNGDATA', $r['body']);
        $this->assertSame(200, $r['status']);
        $this->assertSame('image/png', $r['content_type']);
    }

    public function test_pruned_tile_falls_back_to_ocean() {
        $r = $this->endpoint()->resolve(3, 2, 2);   // reader returns null -> ocean fallback
        $this->assertSame('ocean', $r['source']);
        $this->assertSame(200, $r['status']);
    }

    public function test_out_of_range_zoom_is_404() {
        $r = $this->endpoint()->resolve(20, 0, 0);
        $this->assertSame(404, $r['status']);
    }
}
