<?php
use PHPUnit\Framework\TestCase;

class ExtractorTest extends TestCase {

    private $dest;

    protected function setUp(): void {
        $this->dest = sys_get_temp_dir() . '/pt_extract_' . uniqid();
    }

    protected function tearDown(): void {
        Permatiles_Extractor::rrmdir($this->dest);
    }

    // mini.pmtiles holds z0/0/0=AAA, z1/0/0=BBB, z1/1/1=CCC, z2/2/1=DDD (max_zoom 2); all else absent.
    private function resolver() {
        $reader = new Permatiles_PMTiles_Reader(__DIR__ . '/fixtures/mini.pmtiles');
        return function ($z, $x, $y) use ($reader) { return $reader->get_tile($z, $x, $y); };
    }

    public function test_materialises_every_position_land_and_ocean() {
        $ocean = __DIR__ . '/fixtures/ocean.png';
        $res = Permatiles_Extractor::extract(2, $this->resolver(), $ocean, $this->dest);

        // 4 land tiles from the fixture; the rest of the 1+4+16=21 positions are ocean
        $this->assertSame(4, $res['tiles']);
        $this->assertSame(17, $res['ocean']);

        $this->assertSame('AAA', file_get_contents("$this->dest/0/0/0.png"));
        $this->assertSame('BBB', file_get_contents("$this->dest/1/0/0.png"));
        $this->assertSame('CCC', file_get_contents("$this->dest/1/1/1.png"));
        $this->assertSame('DDD', file_get_contents("$this->dest/2/2/1.png"));

        // an open-water position exists and carries the ocean tile's bytes (never a 404 -> WP)
        $this->assertSame(file_get_contents($ocean), file_get_contents("$this->dest/1/0/1.png"));
        $this->assertFileExists("$this->dest/2/3/3.png");     // z2 grid is 4x4 (0..3); corner is ocean
    }

    public function test_rebuild_drops_stale_tiles() {
        $ocean = __DIR__ . '/fixtures/ocean.png';
        mkdir($this->dest, 0777, true);
        file_put_contents("$this->dest/stale.png", 'old');   // leftover from a previous release

        Permatiles_Extractor::extract(1, $this->resolver(), $ocean, $this->dest);

        $this->assertFileDoesNotExist("$this->dest/stale.png");   // tree wiped and rebuilt
        $this->assertFileExists("$this->dest/0/0/0.png");
    }
}
