package com.msrap.controller;

import com.msrap.model.AnalyticsResult;
import com.msrap.model.FactorLoading;
import com.msrap.model.RegimeState;
import com.msrap.service.AnalyticsService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/analytics")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class AnalyticsController {

    private final AnalyticsService analyticsService;

    // ─── Volatility ───────────────────────────────────

    @GetMapping("/volatility/{symbol}")
    public ResponseEntity<List<AnalyticsResult>> getVolatility(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "365") int days) {
        return ResponseEntity.ok(analyticsService.getVolatilityMetrics(symbol, days));
    }

    @GetMapping("/volatility/{symbol}/{metric}")
    public ResponseEntity<List<AnalyticsResult>> getVolMetric(
            @PathVariable String symbol,
            @PathVariable String metric,
            @RequestParam(defaultValue = "365") int days) {
        return ResponseEntity.ok(analyticsService.getVolMetricSeries(symbol, metric, days));
    }

    // ─── Regime ───────────────────────────────────────

    @GetMapping("/regime/{symbol}")
    public ResponseEntity<List<RegimeState>> getRegimeHistory(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "365") int days) {
        return ResponseEntity.ok(analyticsService.getRegimeHistory(symbol, days));
    }

    @GetMapping("/regime/{symbol}/current")
    public ResponseEntity<RegimeState> getCurrentRegime(@PathVariable String symbol) {
        return analyticsService.getCurrentRegime(symbol)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    // ─── Factor ───────────────────────────────────────

    @GetMapping("/factor/{symbol}")
    public ResponseEntity<List<FactorLoading>> getFactorLoadings(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "252") int window,
            @RequestParam(defaultValue = "730") int days) {
        return ResponseEntity.ok(analyticsService.getFactorLoadings(symbol, window, days));
    }

    @GetMapping("/factor/{symbol}/latest")
    public ResponseEntity<FactorLoading> getLatestFactors(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "252") int window) {
        return analyticsService.getLatestFactorLoading(symbol, window)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    // ─── Summary ──────────────────────────────────────

    @GetMapping("/summary/{symbol}")
    public ResponseEntity<Map<String, Object>> getSummary(@PathVariable String symbol) {
        return ResponseEntity.ok(analyticsService.getSummaryCard(symbol));
    }

    // ─── Trigger workers (manual) ─────────────────────

    @PostMapping("/run/volatility/{symbol}")
    public ResponseEntity<String> triggerVolatility(@PathVariable String symbol) {
        analyticsService.runVolatilityWorker(symbol);
        return ResponseEntity.ok("Volatility worker triggered for " + symbol);
    }

    @PostMapping("/run/regime/{symbol}")
    public ResponseEntity<String> triggerRegime(@PathVariable String symbol) {
        analyticsService.runRegimeWorker(symbol);
        return ResponseEntity.ok("Regime worker triggered for " + symbol);
    }

    @PostMapping("/run/factor/{symbol}")
    public ResponseEntity<String> triggerFactor(@PathVariable String symbol) {
        analyticsService.runFactorWorker(symbol);
        return ResponseEntity.ok("Factor worker triggered for " + symbol);
    }

    @PostMapping("/run/all/{symbol}")
    public ResponseEntity<String> triggerAll(@PathVariable String symbol) {
        analyticsService.runVolatilityWorker(symbol);
        analyticsService.runRegimeWorker(symbol);
        analyticsService.runFactorWorker(symbol);
        return ResponseEntity.ok("All workers triggered for " + symbol);
    }
}
