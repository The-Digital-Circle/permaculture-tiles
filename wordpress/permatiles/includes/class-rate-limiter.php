<?php
if (! defined('ABSPATH')) { exit; }

interface Permatiles_Store {
    public function get($key);
    public function set($key, $value, $ttl);
}

/** Per-IP token bucket. `rate` tokens/sec, capacity `burst`. allow() costs one token. */
class Permatiles_Rate_Limiter {

    private $store;
    private $rate;
    private $burst;
    private $clock;

    public function __construct(Permatiles_Store $store, $rate, $burst, $clock = null) {
        $this->store = $store;
        $this->rate  = (float) $rate;
        $this->burst = (float) $burst;
        $this->clock = $clock ?: function () { return microtime(true); };
    }

    public function allow($ip) {
        $key = 'permatiles_rl_' . md5($ip);
        $now = (float) call_user_func($this->clock);
        $state = $this->store->get($key);
        if (! is_array($state)) {
            $state = ['tokens' => $this->burst, 'ts' => $now];
        }
        $elapsed = max(0.0, $now - $state['ts']);
        $tokens = min($this->burst, $state['tokens'] + $elapsed * $this->rate);
        if ($tokens < 1.0) {
            $this->store->set($key, ['tokens' => $tokens, 'ts' => $now], 3600);
            return false;
        }
        $this->store->set($key, ['tokens' => $tokens - 1.0, 'ts' => $now], 3600);
        return true;
    }
}
