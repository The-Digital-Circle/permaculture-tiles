<?php
use PHPUnit\Framework\TestCase;

class EndpointTest extends TestCase {
    private function endpoint($format = 'png') {
        $manifest = new class($format) {
            private $format;
            public function __construct($format) { $this->format = $format; }
            public function maxzoom() { return 5; }
            public function tile_format() { return $this->format; }
            public function file_for($z, $x, $y) { return 'band.pmtiles'; }
        };
        $factory = function ($file) {
            return new class {
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

    public function test_content_type_follows_the_tile_format() {
        $r = $this->endpoint('webp')->resolve(3, 1, 1);
        $this->assertSame('image/webp', $r['content_type']);
        $this->assertSame('image/webp', $this->endpoint('webp')->resolve(0, 0, 0)['content_type']);  // ocean
        $this->assertSame('image/png', $this->endpoint('png')->resolve(3, 1, 1)['content_type']);
    }
}
