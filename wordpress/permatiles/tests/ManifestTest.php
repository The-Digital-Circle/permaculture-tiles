<?php
use PHPUnit\Framework\TestCase;

class ManifestTest extends TestCase {
    private function manifest() {
        return new Permatiles_Manifest(__DIR__ . '/fixtures');
    }

    public function test_basic_fields() {
        $m = $this->manifest();
        $this->assertSame(8, $m->maxzoom());
        $this->assertSame('Natural Earth', $m->attribution());
        $this->assertSame(__DIR__ . '/fixtures/ocean.png', $m->ocean_tile_path());
    }

    public function test_routing_by_zoom() {
        $m = $this->manifest();
        $this->assertSame('tiles-z0-6.pmtiles', basename($m->file_for(3, 1, 1)));
        $this->assertSame('tiles-z7-8.pmtiles', basename($m->file_for(8, 5, 5)));
        $this->assertNull($m->file_for(9, 0, 0));    // beyond maxzoom
    }
}
