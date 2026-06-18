<?php
if (! defined('ABSPATH')) { exit; }

/** Settings → Permatiles: toggle, rate-limit, referer allowlist, repo, and a "Pull latest" button. */
class Permatiles_Admin {

    public function hooks() {
        add_action('admin_menu', [$this, 'menu']);
        add_action('admin_init', [$this, 'register']);
    }

    public function menu() {
        add_options_page('Permatiles', 'Permatiles', 'manage_options', 'permatiles', [$this, 'render']);
    }

    public function register() {
        register_setting('permatiles', 'permatiles_settings', [$this, 'sanitize']);
    }

    public function sanitize($in) {
        return [
            'enabled'       => empty($in['enabled']) ? 0 : 1,
            'rate_per_sec'  => max(1, (int) ($in['rate_per_sec'] ?? 20)),
            'burst'         => max(1, (int) ($in['burst'] ?? 400)),
            'referer_hosts' => sanitize_textarea_field($in['referer_hosts'] ?? ''),
            'repo'          => sanitize_text_field($in['repo'] ?? 'The-Digital-Circle/permaculture-tiles'),
        ];
    }

    public function render() {
        $s = permatiles_settings();
        $manifest = new Permatiles_Manifest(PERMATILES_DATA_DIR);
        $have = $manifest->exists();
        $last = get_transient('permatiles_last_pull');
        echo '<div class="wrap"><h1>Permatiles</h1>';
        if (isset($_GET['pulled'])) {
            $ok = $_GET['pulled'] === '1';
            printf('<div class="notice notice-%s"><p>%s</p></div>',
                $ok ? 'success' : 'error',
                $last ? esc_html($last['message']) : ($ok ? 'Pulled.' : 'Pull failed.'));
        }
        echo '<p>Tiles installed: <strong>' . ($have ? 'yes (maxzoom ' . (int) $manifest->maxzoom() . ')' : 'no') . '</strong></p>';
        echo '<form method="post" action="options.php">';
        settings_fields('permatiles');
        echo '<table class="form-table">';
        printf('<tr><th>Enabled</th><td><label><input type="checkbox" name="permatiles_settings[enabled]" value="1" %s> serve tiles at /permatiles/{z}/{x}/{y}.png</label></td></tr>', checked($s['enabled'], 1, false));
        printf('<tr><th>Rate (tiles/sec/IP)</th><td><input type="number" name="permatiles_settings[rate_per_sec]" value="%d" min="1"></td></tr>', (int) $s['rate_per_sec']);
        printf('<tr><th>Burst</th><td><input type="number" name="permatiles_settings[burst]" value="%d" min="1"></td></tr>', (int) $s['burst']);
        printf('<tr><th>Referer hosts</th><td><textarea name="permatiles_settings[referer_hosts]" rows="3" cols="40" placeholder="perma.earth&#10;map.perma.earth">%s</textarea><p class="description">One host per line. Empty = allow any (still rate-limited).</p></td></tr>', esc_textarea($s['referer_hosts']));
        printf('<tr><th>Release repo</th><td><input type="text" name="permatiles_settings[repo]" value="%s" size="40"></td></tr>', esc_attr($s['repo']));
        echo '</table>';
        submit_button();
        echo '</form>';
        echo '<hr><h2>Tiles</h2><form method="post" action="' . esc_url(admin_url('admin-post.php')) . '">';
        wp_nonce_field('permatiles_pull');
        echo '<input type="hidden" name="action" value="permatiles_pull">';
        submit_button('Pull latest tiles', 'secondary');
        echo '</form></div>';
    }
}
