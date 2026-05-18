package com.msrap.config;

import lombok.Getter;
import lombok.Setter;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * Strongly-typed binding for the {@code msrap.ingestion.*} block in application.yml.
 *
 * <p>Replaces {@code @Value("${msrap.ingestion.symbols}")} list injection in
 * {@link com.msrap.scheduler.MarketScheduler}, which is fragile when the YAML
 * list has more than one entry.</p>
 *
 * <pre>
 * msrap:
 *   ingestion:
 *     symbols:
 *       - RELIANCE.NS
 *       - TCS.NS
 *     history-days: 1825
 *     schedule-cron: "0 0 6 * * MON-FRI"
 * </pre>
 */
@Getter
@Setter
@Component
@ConfigurationProperties(prefix = "msrap.ingestion")
public class IngestionProperties {

    /** NSE ticker symbols to ingest daily. */
    private List<String> symbols = new ArrayList<>();

    /** How many calendar days of history to backfill on first run. */
    private int historyDays = 1825;

    /** Cron expression for the daily ingestion schedule (informational — actual
     *  schedule is hardcoded in {@link com.msrap.scheduler.MarketScheduler}). */
    private String scheduleCron = "0 0 6 * * MON-FRI";
}
