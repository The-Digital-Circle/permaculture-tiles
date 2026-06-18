<?php
/**
 * Plugin Name: Permatiles
 * Description: Serves the self-hosted watercolour basemap (PMTiles) for the perma.earth global map.
 * Version: 0.1.0
 * Requires PHP: 7.4
 */

if (! defined('ABSPATH')) {
    exit;
}

define('PERMATILES_VERSION', '0.1.0');
define('PERMATILES_DIR', plugin_dir_path(__FILE__));
define('PERMATILES_DATA_DIR', trailingslashit(wp_upload_dir()['basedir']) . 'permatiles');

require_once PERMATILES_DIR . 'includes/class-pmtiles-reader.php';
require_once PERMATILES_DIR . 'includes/class-manifest.php';
require_once PERMATILES_DIR . 'includes/class-rate-limiter.php';
require_once PERMATILES_DIR . 'includes/class-tile-endpoint.php';
require_once PERMATILES_DIR . 'includes/class-updater.php';
require_once PERMATILES_DIR . 'includes/class-admin.php';

/** Settings with defaults. */
function permatiles_settings() {
    return wp_parse_args(get_option('permatiles_settings', []), [
        'enabled'        => 0,
        'rate_per_sec'   => 20,      // ~1200 tiles/min sustained per IP
        'burst'          => 400,     // a full map view is ~tens of tiles; 400 covers pan bursts
        'referer_hosts'  => '',      // newline list; empty = allow any (still rate-limited)
        'repo'           => 'The-Digital-Circle/permaculture-tiles',
    ]);
}

/** Transient-backed store for the rate limiter. */
class Permatiles_Transient_Store implements Permatiles_Store {
    public function get($key) { $v = get_transient($key); return $v === false ? null : $v; }
    public function set($key, $value, $ttl) { set_transient($key, $value, $ttl); }
}

add_action('init', function () {
    add_rewrite_rule('^permatiles/(\d+)/(\d+)/(\d+)\.png$',
        'index.php?permatiles_z=$matches[1]&permatiles_x=$matches[2]&permatiles_y=$matches[3]', 'top');
});

add_filter('query_vars', function ($vars) {
    return array_merge($vars, ['permatiles_z', 'permatiles_x', 'permatiles_y']);
});

add_action('template_redirect', function () {
    $z = get_query_var('permatiles_z', null);
    if ($z === null || $z === '') { return; }
    $x = get_query_var('permatiles_x');
    $y = get_query_var('permatiles_y');
    $s = permatiles_settings();

    if (empty($s['enabled'])) { status_header(404); exit; }

    // referer/origin allowlist (empty list = allow any; requests are still rate-limited)
    $hosts = array_filter(array_map('trim', preg_split('/\s+/', (string) $s['referer_hosts'])));
    if ($hosts) {
        $ref = $_SERVER['HTTP_REFERER'] ?? ($_SERVER['HTTP_ORIGIN'] ?? '');
        $host = $ref ? parse_url($ref, PHP_URL_HOST) : '';
        if (! $host || ! in_array($host, $hosts, true)) { status_header(403); exit; }
    }

    // per-IP token-bucket rate limit
    $limiter = new Permatiles_Rate_Limiter(new Permatiles_Transient_Store(),
        (float) $s['rate_per_sec'], (float) $s['burst']);
    $ip = $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
    if (! $limiter->allow($ip)) {
        status_header(429);
        header('Retry-After: 1');
        exit;
    }

    $manifest = new Permatiles_Manifest(PERMATILES_DATA_DIR);
    if (! $manifest->exists()) { status_header(503); exit; }
    $endpoint = new Permatiles_Tile_Endpoint($manifest,
        function ($file) { return new Permatiles_PMTiles_Reader($file); },
        $manifest->ocean_tile_path());

    $res = $endpoint->resolve($z, $x, $y);
    status_header($res['status']);
    if ($res['body'] === null) { exit; }
    header('Content-Type: ' . $res['content_type']);
    header('Content-Length: ' . strlen($res['body']));
    header('Cache-Control: public, max-age=2592000, immutable');   // 30 days; tiles are versioned by release
    header('X-Permatiles-Source: ' . $res['source']);
    echo $res['body'];
    exit;
});

register_activation_hook(__FILE__, function () {
    add_rewrite_rule('^permatiles/(\d+)/(\d+)/(\d+)\.png$',
        'index.php?permatiles_z=$matches[1]&permatiles_x=$matches[2]&permatiles_y=$matches[3]', 'top');
    flush_rewrite_rules();
});
register_deactivation_hook(__FILE__, 'flush_rewrite_rules');
