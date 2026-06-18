<?php
use PHPUnit\Framework\TestCase;

class SmokeTest extends TestCase {
    public function test_classes_load() {
        $this->assertTrue(class_exists('Permatiles_PMTiles_Reader'));
        $this->assertTrue(class_exists('Permatiles_Rate_Limiter'));
    }
}
