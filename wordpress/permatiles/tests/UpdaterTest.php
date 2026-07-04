<?php
use PHPUnit\Framework\TestCase;

class UpdaterTest extends TestCase {

    private $dir;

    protected function setUp(): void {
        $this->dir = sys_get_temp_dir() . '/permatiles_prune_' . uniqid();
        mkdir($this->dir);
    }

    protected function tearDown(): void {
        foreach (glob($this->dir . '/*') as $f) { @unlink($f); }
        @rmdir($this->dir);
    }

    private function touch_all(array $names) {
        foreach ($names as $n) { file_put_contents($this->dir . '/' . $n, 'x'); }
    }

    public function test_prune_removes_stale_band_keeps_current_set() {
        $this->touch_all(['manifest.json', 'ocean.png', 'tiles-z0-7.pmtiles', 'tiles-z0-8.pmtiles']);
        $keep = ['manifest.json', 'ocean.png', 'tiles-z0-7.pmtiles'];

        $removed = Permatiles_Updater::prune_dir($this->dir, $keep);

        $this->assertSame(['tiles-z0-8.pmtiles'], $removed);        // only the orphan is dropped
        $this->assertFileDoesNotExist($this->dir . '/tiles-z0-8.pmtiles');
        foreach ($keep as $n) { $this->assertFileExists($this->dir . '/' . $n); }
    }

    public function test_prune_noop_when_nothing_stale() {
        $keep = ['manifest.json', 'ocean.png', 'tiles-z0-7.pmtiles'];
        $this->touch_all($keep);

        $this->assertSame([], Permatiles_Updater::prune_dir($this->dir, $keep));
        foreach ($keep as $n) { $this->assertFileExists($this->dir . '/' . $n); }
    }

    public function test_prune_leaves_incoming_dotdir_alone() {
        $this->touch_all(['manifest.json']);
        mkdir($this->dir . '/.incoming');
        file_put_contents($this->dir . '/.incoming/partial', 'x');

        Permatiles_Updater::prune_dir($this->dir, ['manifest.json']);

        $this->assertDirectoryExists($this->dir . '/.incoming');    // dotfiles/dirs untouched
        @unlink($this->dir . '/.incoming/partial');
        @rmdir($this->dir . '/.incoming');
    }
}
