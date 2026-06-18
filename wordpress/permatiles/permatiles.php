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
