<?php
use PHPUnit\Framework\TestCase;

class ArrayStore implements Permatiles_Store {
    public $data = [];
    public function get($k) { return $this->data[$k] ?? null; }
    public function set($k, $v, $ttl) { $this->data[$k] = $v; }
}

class RateLimiterTest extends TestCase {
    public function test_burst_then_block() {
        $store = new ArrayStore();
        $now = 1000.0;
        // 1 token/sec, burst 3
        $rl = new Permatiles_Rate_Limiter($store, 1.0, 3, function () use (&$now) { return $now; });
        $this->assertTrue($rl->allow('1.2.3.4'));   // 3 -> 2
        $this->assertTrue($rl->allow('1.2.3.4'));   // 2 -> 1
        $this->assertTrue($rl->allow('1.2.3.4'));   // 1 -> 0
        $this->assertFalse($rl->allow('1.2.3.4'));  // 0 -> blocked
    }

    public function test_refill_over_time() {
        $store = new ArrayStore();
        $now = 1000.0;
        $rl = new Permatiles_Rate_Limiter($store, 1.0, 3, function () use (&$now) { return $now; });
        for ($i = 0; $i < 3; $i++) { $rl->allow('ip'); }
        $this->assertFalse($rl->allow('ip'));
        $now += 2.0;                                  // refill 2 tokens
        $this->assertTrue($rl->allow('ip'));
        $this->assertTrue($rl->allow('ip'));
        $this->assertFalse($rl->allow('ip'));
    }

    public function test_separate_ips_independent() {
        $store = new ArrayStore();
        $rl = new Permatiles_Rate_Limiter($store, 1.0, 1, function () { return 5.0; });
        $this->assertTrue($rl->allow('a'));
        $this->assertFalse($rl->allow('a'));
        $this->assertTrue($rl->allow('b'));
    }
}
