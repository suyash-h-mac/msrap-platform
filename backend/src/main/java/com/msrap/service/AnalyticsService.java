package com.msrap.service;

import com.msrap.model.AnalyticsResult;
import com.msrap.model.FactorLoading;
import com.msrap.model.RegimeState;
import com.msrap.repository.AnalyticsResultRepository;
import com.msrap.repository.FactorLoadingRepository;
import com.msrap.repository.RegimeStateRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class AnalyticsService {

    private final AnalyticsResultRepository analyticsRepo;
    private final RegimeStateRepository regimeRepo;
    private final FactorLoadingRepository factorRepo;

    @Value("${msrap.analytics.python-path:/app/analytics}")
    private String pythonPath;

    // ─────────────────────────────
    // Run analytics workers
    // ─────────────────────────────

    public void runVolatilityWorker(String symbol) {
        runPythonWorker("volatility/vol_worker.py", symbol);
    }

    public void runRegimeWorker(String symbol) {
        runPythonWorker("regime/regime_worker.py", symbol);
    }

    public void runFactorWorker(String symbol) {
        runPythonWorker("factor/factor_worker.py", symbol);
    }

    private void runPythonWorker(String script, String symbol) {
        log.info("Running {} for {}", script, symbol);
        try {
            ProcessBuilder pb = new ProcessBuilder(
                    "python3",
                    pythonPath + "/" + script,
                    "--symbol", symbol
            );
            pb.redirectErrorStream(false);
            Process proc = pb.start();

            try (BufferedReader err = new BufferedReader(new InputStreamReader(proc.getErrorStream()))) {
                String line;
                while ((line = err.readLine()) != null) {
                    log.debug("[{}] {}", script, line);
                }
            }

            int exit = proc.waitFor();
            if (exit != 0) {
                log.error("Worker {} for {} exited with code {}", script, symbol, exit);
            } else {
                log.info("Worker {} for {} completed", script, symbol);
            }
        } catch (Exception e) {
            log.error("Failed to run {} for {}: {}", script, symbol, e.getMessage(), e);
        }
    }

    // ─────────────────────────────
    // Query analytics results
    // ─────────────────────────────

    public List<AnalyticsResult> getVolatilityMetrics(String symbol, int days) {
        Instant from = Instant.now().minus(days, ChronoUnit.DAYS);
        return analyticsRepo.findSince(symbol, "volatility", from);
    }

    public List<AnalyticsResult> getVolMetricSeries(String symbol, String metric, int days) {
        return analyticsRepo.findBySymbolAndModuleAndMetricOrderByTsAsc(symbol, "volatility", metric);
    }

    public List<RegimeState> getRegimeHistory(String symbol, int days) {
        Instant from = Instant.now().minus(days, ChronoUnit.DAYS);
        return regimeRepo.findBySymbolAndTsBetweenOrderByTsAsc(symbol, from, Instant.now());
    }

    public Optional<RegimeState> getCurrentRegime(String symbol) {
        return regimeRepo.findLatest(symbol);
    }

    public List<FactorLoading> getFactorLoadings(String symbol, int windowDays, int historyDays) {
        Instant from = Instant.now().minus(historyDays, ChronoUnit.DAYS);
        return factorRepo.findBySymbolAndWindowDaysAndTsBetweenOrderByTsAsc(
                symbol, (short) windowDays, from, Instant.now());
    }

    public Optional<FactorLoading> getLatestFactorLoading(String symbol, int windowDays) {
        return factorRepo.findLatest(symbol, (short) windowDays);
    }

    public Map<String, Object> getSummaryCard(String symbol) {
        Optional<RegimeState> regime = getCurrentRegime(symbol);
        Optional<FactorLoading> factors = getLatestFactorLoading(symbol, 252);
        List<AnalyticsResult> latestVol = analyticsRepo.findLatestN(symbol, "volatility", 10);

        return Map.of(
                "symbol", symbol,
                "regime", regime.map(r -> Map.of(
                        "state", r.getState(),
                        "label", r.getStateLabel() != null ? r.getStateLabel() : "unknown",
                        "ts", r.getTs()
                )).orElse(Map.of("state", -1, "label", "not computed")),
                "factors", factors.map(f -> Map.of(
                        "betaMarket",   f.getBetaMarket(),
                        "betaSize",     f.getBetaSize(),
                        "betaValue",    f.getBetaValue(),
                        "betaMomentum", f.getBetaMomentum(),
                        "rSquared",     f.getRSquared(),
                        "ts",           f.getTs()
                )).orElse(Map.of("status", "not computed")),
                "volatility", latestVol.stream()
                        .collect(java.util.stream.Collectors.toMap(
                                AnalyticsResult::getMetric,
                                r -> r.getValue() != null ? r.getValue() : r.getValueStr(),
                                (a, b) -> b
                        ))
        );
    }
}
