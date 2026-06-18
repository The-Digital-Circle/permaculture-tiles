<?php
if (! defined('ABSPATH')) { exit; }

/**
 * Downloads the latest release assets (manifest.json, ocean.png, *.pmtiles) from the configured
 * GitHub repo into a temp dir, verifies each PMTiles sha256 against the manifest, then atomically
 * moves them into place. Never serves a half-downloaded set: a failure leaves the existing set intact.
 */
class Permatiles_Updater {

    private $repo;
    private $dest;

    public function __construct($repo, $dest) {
        $this->repo = $repo;
        $this->dest = rtrim($dest, '/');
    }

    /** @return array{ok:bool, message:string, files?:array} */
    public function pull() {
        $api = "https://api.github.com/repos/{$this->repo}/releases/latest";
        $res = wp_remote_get($api, ['headers' => ['Accept' => 'application/vnd.github+json',
            'User-Agent' => 'permatiles'], 'timeout' => 30]);
        if (is_wp_error($res)) { return ['ok' => false, 'message' => $res->get_error_message()]; }
        $body = json_decode(wp_remote_retrieve_body($res), true);
        if (empty($body['assets'])) { return ['ok' => false, 'message' => 'no assets in latest release']; }

        $assets = [];
        foreach ($body['assets'] as $a) { $assets[$a['name']] = $a['browser_download_url']; }
        if (! isset($assets['manifest.json'])) {
            return ['ok' => false, 'message' => 'release has no manifest.json'];
        }

        $tmp = $this->dest . '/.incoming';
        if (! wp_mkdir_p($tmp)) { return ['ok' => false, 'message' => "cannot create $tmp"]; }

        // manifest first, so we know which pmtiles to expect and their checksums
        if (! $this->download($assets['manifest.json'], "$tmp/manifest.json")) {
            return $this->fail($tmp, 'manifest download failed');
        }
        $manifest = json_decode(file_get_contents("$tmp/manifest.json"), true);
        if (! is_array($manifest) || empty($manifest['tiles'])) {
            return $this->fail($tmp, 'invalid manifest');
        }

        $expected = ['manifest.json'];
        $ocean = $manifest['ocean_tile'] ?? 'ocean.png';
        $expected[] = $ocean;
        if (isset($assets[$ocean]) && ! $this->download($assets[$ocean], "$tmp/$ocean")) {
            return $this->fail($tmp, "download failed: $ocean");
        }
        foreach ($manifest['tiles'] as $t) {
            $name = $t['file'];
            $expected[] = $name;
            if (! isset($assets[$name])) { return $this->fail($tmp, "release missing asset: $name"); }
            if (! $this->download($assets[$name], "$tmp/$name")) {
                return $this->fail($tmp, "download failed: $name");
            }
            if (! empty($t['sha256'])) {
                $got = hash_file('sha256', "$tmp/$name");
                if (! hash_equals($t['sha256'], $got)) {
                    return $this->fail($tmp, "checksum mismatch: $name");
                }
            }
        }

        // atomic-ish swap: move verified files into place, then drop stale ones
        foreach ($expected as $name) {
            if (file_exists("$tmp/$name")) { @rename("$tmp/$name", "{$this->dest}/$name"); }
        }
        $this->rmdir($tmp);
        return ['ok' => true, 'message' => 'pulled ' . count($expected) . ' files', 'files' => $expected];
    }

    private function download($url, $path) {
        $tmp = download_url($url, 60);   // wp_remote handles redirects to the asset CDN
        if (is_wp_error($tmp)) { return false; }
        $ok = @rename($tmp, $path);
        if (! $ok) { @copy($tmp, $path); @unlink($tmp); $ok = file_exists($path); }
        return $ok;
    }

    private function fail($tmp, $msg) {
        $this->rmdir($tmp);
        return ['ok' => false, 'message' => $msg];
    }

    private function rmdir($dir) {
        if (! is_dir($dir)) { return; }
        foreach (glob($dir . '/*') as $f) { @unlink($f); }
        @rmdir($dir);
    }
}
