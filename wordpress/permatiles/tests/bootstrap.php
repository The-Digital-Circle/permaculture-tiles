<?php
if (! defined('ABSPATH')) { define('ABSPATH', __DIR__); }
require __DIR__ . '/../includes/class-pmtiles-reader.php';
require __DIR__ . '/../includes/class-manifest.php';
require __DIR__ . '/../includes/class-rate-limiter.php';
require __DIR__ . '/../includes/class-tile-endpoint.php';
require __DIR__ . '/../includes/class-updater.php';

// Minimal stubs for the WordPress helpers the extractor touches (real WP provides these at runtime).
if (! function_exists('wp_mkdir_p')) {
    function wp_mkdir_p($dir) { return is_dir($dir) || mkdir($dir, 0777, true); }
}
require __DIR__ . '/../includes/class-extractor.php';
