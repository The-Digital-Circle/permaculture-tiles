<?php
use PHPUnit\Framework\TestCase;

class ReaderTest extends TestCase {
    private function reader() {
        return new Permatiles_PMTiles_Reader(__DIR__ . '/fixtures/mini.pmtiles');
    }

    public function test_zxy_to_tileid_matches_reference() {
        // values from pmtiles.tile.zxy_to_tileid
        $this->assertSame(0, Permatiles_PMTiles_Reader::zxy_to_tileid(0, 0, 0));
        $this->assertSame(1, Permatiles_PMTiles_Reader::zxy_to_tileid(1, 0, 0));
        $this->assertSame(2, Permatiles_PMTiles_Reader::zxy_to_tileid(1, 0, 1));
        $this->assertSame(3, Permatiles_PMTiles_Reader::zxy_to_tileid(1, 1, 1));
        $this->assertSame(4, Permatiles_PMTiles_Reader::zxy_to_tileid(1, 1, 0));
        $this->assertSame(5, Permatiles_PMTiles_Reader::zxy_to_tileid(2, 0, 0));
    }

    public function test_header_parsed() {
        $h = $this->reader()->header();
        $this->assertSame(0, $h['min_zoom']);
        $this->assertSame(2, $h['max_zoom']);
        $this->assertSame(2, $h['tile_type']);            // PNG
        $this->assertSame(2, $h['internal_compression']); // gzip
    }

    public function test_get_existing_tiles() {
        $r = $this->reader();
        $this->assertSame('AAA', $r->get_tile(0, 0, 0));
        $this->assertSame('BBB', $r->get_tile(1, 0, 0));
        $this->assertSame('CCC', $r->get_tile(1, 1, 1));
        $this->assertSame('DDD', $r->get_tile(2, 2, 1));
    }

    public function test_missing_tile_returns_null() {
        $this->assertNull($this->reader()->get_tile(2, 0, 0));   // absent -> pruned/ocean
        $this->assertNull($this->reader()->get_tile(5, 0, 0));   // out of zoom range
    }
}
