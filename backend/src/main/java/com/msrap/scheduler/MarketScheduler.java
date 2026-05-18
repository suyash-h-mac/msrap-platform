package com.msrap.scheduler;

import com.msrap.config.IngestionProperties;
import com.msrap.service.AnalyticsService;
import com.msrap.service.IngestionService;
import com.msrap.service.MarketDataService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

@Slf4j
@Component
@RequiredArgsConstructor
public class MarketScheduler {

    private final IngestionService ingestionService;
    private final AnalyticsService analyticsService;
    private final MarketDataService marketDataService;
    private final IngestionProperties ingestionProperties;

    private List<String> symbols() {
        return ingestionProperties.getSymbols();
    }

    private final ExecutorService pool = Executors.newFixedThreadPool(4);

    /** Daily ingestion — runs at 06:00 IST on weekdays (00:30 UTC) */
    @Scheduled(cron = "0 30 0 * * MON-FRI", zone = "UTC")
    public void dailyIngestion() {
        log.info("Starting daily ingestion for {} symbols", symbols().size());
        for (String symbol : symbols()) {
            pool.submit(() -> {
                ingestionService.ingestSymbol(symbol, "1d");
            });
        }
    }

    /** Run analytics after ingestion — 07:00 IST / 01:30 UTC */
    @Scheduled(cron = "0 30 1 * * MON-FRI", zone = "UTC")
    public void dailyAnalytics() {
        log.info("Starting daily analytics run");
        for (String symbol : symbols()) {
            pool.submit(() -> {
                try {
                    analyticsService.runVolatilityWorker(symbol);
                    analyticsService.runRegimeWorker(symbol);
                    analyticsService.runFactorWorker(symbol);
                } catch (Exception e) {
                    log.error("Analytics failed for {}: {}", symbol, e.getMessage());
                }
            });
        }
    }

    /** Intraday refresh for indices — every hour during market hours (03:45–10:00 UTC = 09:15–15:30 IST) */
    @Scheduled(cron = "0 0 3-10 * * MON-FRI", zone = "UTC")
    public void intradayRefresh() {
        List<String> indices = List.of("^NSEI", "^NSEBANK");
        for (String sym : indices) {
            pool.submit(() -> ingestionService.ingestSymbol(sym, "1d"));
        }
    }

    /** Full historical backfill — runs once at startup if triggered manually */
    public void backfillAll() {
        log.info("Starting full historical backfill for {} symbols", symbols().size());
        for (String symbol : symbols()) {
            pool.submit(() -> ingestionService.ingestSymbol(symbol, "1d"));
        }
    }
}
