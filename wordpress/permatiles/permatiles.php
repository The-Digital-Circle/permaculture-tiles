<?php
/**
 * Plugin Name: Permatiles
 * Description: Serves the self-hosted watercolour basemap (PMTiles) for the perma.earth global map.
 * Version: 0.1.5
 * Requires PHP: 7.4
 */

if (! defined('ABSPATH')) {
    exit;
}

define('PERMATILES_VERSION', '0.1.5');
define('PERMATILES_DIR', plugin_dir_path(__FILE__));
define('PERMATILES_DATA_DIR', trailingslashit(wp_upload_dir()['basedir']) . 'permatiles');

require_once PERMATILES_DIR . 'includes/class-pmtiles-reader.php';
require_once PERMATILES_DIR . 'includes/class-manifest.php';
require_once PERMATILES_DIR . 'includes/class-rate-limiter.php';
require_once PERMATILES_DIR . 'includes/class-tile-endpoint.php';
require_once PERMATILES_DIR . 'includes/class-updater.php';
require_once PERMATILES_DIR . 'includes/class-extractor.php';
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

// Without this, WordPress canonical-redirects (301) the tile URL to a trailing-slashed variant
// (/.../2.png -> /.../2.png/), which Leaflet won't follow — so tiles silently fail to load.
add_filter('redirect_canonical', function ($redirect_url) {
    $z = get_query_var('permatiles_z', null);
    return ($z === null || $z === '') ? $redirect_url : false;
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

add_action('admin_post_permatiles_pull', function () {
    if (! current_user_can('manage_options') || ! check_admin_referer('permatiles_pull')) {
        wp_die('forbidden');
    }
    $s = permatiles_settings();
    $updater = new Permatiles_Updater($s['repo'], PERMATILES_DATA_DIR);
    wp_mkdir_p(PERMATILES_DATA_DIR);
    $r = $updater->pull();
    if ($r['ok']) {
        $r['extracted'] = Permatiles_Extractor::run(PERMATILES_DATA_DIR);
        if (! empty($r['extracted']['ok'])) { permatiles_drop_source(); }
    }
    set_transient('permatiles_last_pull', $r, 600);
    wp_safe_redirect(admin_url('options-general.php?page=permatiles&pulled=' . ($r['ok'] ? '1' : '0')));
    exit;
});

/**
 * Delete the source PMTiles once the static tree is built and verified — the map serves the static
 * tiles, so the multi-hundred-MB PMTiles is dead weight on disk. Guarded on the tree existing, so we
 * never drop the source when there is nothing to fall back to.
 */
function permatiles_drop_source() {
    if (! is_file(PERMATILES_DATA_DIR . '/tiles/0/0/0.png')) { return 0; }
    $manifest = new Permatiles_Manifest(PERMATILES_DATA_DIR);
    $n = 0;
    foreach ($manifest->tile_files() as $f) { if (@unlink($f)) { $n++; } }
    return $n;
}

if (defined('WP_CLI') && WP_CLI) {
    // Pull the latest release, expand it into the static pyramid the map serves, then drop the source.
    WP_CLI::add_command('permatiles pull', function () {
        $s = permatiles_settings();
        wp_mkdir_p(PERMATILES_DATA_DIR);
        $r = (new Permatiles_Updater($s['repo'], PERMATILES_DATA_DIR))->pull();
        if (! $r['ok']) { WP_CLI::error($r['message']); }
        WP_CLI::log($r['message']);
        $e = Permatiles_Extractor::run(PERMATILES_DATA_DIR);
        if (empty($e['ok'])) { WP_CLI::error('extract failed: ' . ($e['message'] ?? 'unknown')); }
        $dropped = permatiles_drop_source();
        WP_CLI::success("extracted {$e['tiles']} land + {$e['ocean']} ocean tiles; dropped {$dropped} source pmtiles");
    });

    // Re-expand the static pyramid from files already on disk (needs the source pmtiles present).
    WP_CLI::add_command('permatiles extract', function () {
        $e = Permatiles_Extractor::run(PERMATILES_DATA_DIR);
        if (empty($e['ok'])) { WP_CLI::error($e['message'] ?? 'extract failed'); }
        WP_CLI::success("extracted {$e['tiles']} land + {$e['ocean']} ocean tiles");
    });
}

if (is_admin()) {
    (new Permatiles_Admin())->hooks();
}

/**
 * Feed the watercolour basemap to the federation map's filterable base layer. Only when enabled and
 * the STATIC tile pyramid has been extracted; otherwise the federation map falls back to OpenStreetMap.
 *
 * Serves the pre-extracted tiles straight from uploads/ (nginx, no PHP per tile) — NOT the PHP
 * /permatiles/ endpoint, which boots all of WordPress per request (~1.5s) and, under a map view's
 * concurrent tile burst, exhausts PHP-FPM and takes the whole site down.
 *
 * maxZoom is pinned to our native maxzoom (== maxNativeZoom), i.e. overzoom is forbidden. When Leaflet
 * upscales tiles past native it positions the enlarged tiles on fractional pixels, leaving ~1px gaps
 * that the transparent map pane shows through as thin white seams between tiles. Since the federation
 * map takes its own maxZoom from the base layer (map.js sets none), capping the layer here caps the
 * whole map, so Leaflet never upscales and the seams cannot form. Trade-off: the map cannot zoom in
 * past z{maxzoom}; deep marker declustering is limited to that. Raising it needs higher native tiles.
 */
add_filter('murmfed_base_tilelayer', function ($default) {
    // An explicit admin "Base map tiles" setting wins; only auto-supply when nothing is configured.
    if (is_array($default) && ! empty($default['url'])) { return $default; }
    $s = permatiles_settings();
    if (empty($s['enabled'])) { return $default; }
    $manifest = new Permatiles_Manifest(PERMATILES_DATA_DIR);
    if (! $manifest->exists()) { return $default; }
    $tiles_dir = PERMATILES_DATA_DIR . '/tiles';
    if (! is_file($tiles_dir . '/0/0/0.png')) { return $default; }   // not extracted yet -> OSM
    $base = trailingslashit(wp_upload_dir()['baseurl']) . 'permatiles/tiles';
    $ver = (string) @filemtime($tiles_dir . '/0/0/0.png');           // cache-bust when rebuilt
    $mz  = (int) $manifest->maxzoom();
    return [
        'url'           => $base . '/{z}/{x}/{y}.png?v=' . $ver,
        'maxNativeZoom' => $mz,
        'maxZoom'       => $mz,   // pinned to native: forbid overzoom -> no white tile seams
        'attribution'   => $manifest->attribution() ?: 'Natural Earth',
    ];
});
