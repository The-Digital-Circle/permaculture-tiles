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

    public function test_tile_format_defaults_to_png_when_absent() {
        // The v0.2.5 rollback path: an old manifest has no tile_format and must still mean PNG.
        $m = new Permatiles_Manifest(__DIR__ . '/fixtures');
        $this->assertSame('png', $m->tile_format());
    }

    public function test_tile_format_reads_webp() {
        $dir = sys_get_temp_dir() . '/pmt-fmt-' . getmypid();
        @mkdir($dir, 0777, true);
        file_put_contents("$dir/manifest.json", json_encode([
            'tiles' => [], 'ocean_tile' => 'ocean.webp', 'maxzoom' => 2,
            'attribution' => 'fixture', 'tile_format' => 'webp',
        ]));
        $m = new Permatiles_Manifest($dir);
        $this->assertSame('webp', $m->tile_format());
        @unlink("$dir/manifest.json"); @rmdir($dir);
    }

    public function test_tile_format_rejects_junk() {
        // Never let a manifest steer us to an arbitrary extension.
        $dir = sys_get_temp_dir() . '/pmt-junk-' . getmypid();
        @mkdir($dir, 0777, true);
        file_put_contents("$dir/manifest.json", json_encode([
            'tiles' => [], 'maxzoom' => 2, 'tile_format' => '../evil',
        ]));
        $m = new Permatiles_Manifest($dir);
        $this->assertSame('png', $m->tile_format());
        @unlink("$dir/manifest.json"); @rmdir($dir);
    }
}
