package com.msrap.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.msrap.model.EquityOhlcv;
import com.msrap.repository.EquityOhlcvRepository;
import com.msrap.repository.InstrumentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class IngestionService {

    private final EquityOhlcvRepository ohlcvRepository;
    private final InstrumentRepository instrumentRepository;
    private final ObjectMapper objectMapper;

    @Value("${msrap.analytics.python-path:/app/analytics}")
    private String pythonPath;

    @Value("${msrap.ingestion.history-days:1825}")
    private int historyDays;

    @Transactional
    public IngestionResult ingestSymbol(String symbol, String interval) {
        log.info("Ingesting {} @ interval={}", symbol, interval);

        Instant from = determineStartDate(symbol, interval);
        String fromStr = LocalDate.ofInstant(from, ZoneOffset.UTC).toString();

        try {
            List<EquityOhlcv> rows = fetchFromPython(symbol, interval, fromStr);
            if (rows.isEmpty()) {
                log.warn("No data returned for {}", symbol);
                return IngestionResult.empty(symbol);
            }

            List<EquityOhlcv> validated = validate(rows);
            int inserted = upsertBatch(validated);
            log.info("Ingested {} rows for {}", inserted, symbol);
            return IngestionResult.success(symbol, inserted);

        } catch (Exception e) {
            log.error("Ingestion failed for {}: {}", symbol, e.getMessage(), e);
            return IngestionResult.error(symbol, e.getMessage());
        }
    }

    private Instant determineStartDate(String symbol, String interval) {
        return ohlcvRepository.findLatestBySymbolAndInterval(symbol, interval)
                .map(latest -> latest.getTs().plusSeconds(86400))
                .orElse(Instant.now().minusSeconds((long) historyDays * 86400));
    }

    private List<EquityOhlcv> fetchFromPython(String symbol, String interval, String fromDate)
            throws Exception {

        ProcessBuilder pb = new ProcessBuilder(
                "python3",
                pythonPath + "/ingestion/fetcher.py",
                "--symbol", symbol,
                "--interval", interval,
                "--from", fromDate
        );
        pb.redirectErrorStream(false);
        Process proc = pb.start();

        StringBuilder out = new StringBuilder();
        StringBuilder err = new StringBuilder();

        try (BufferedReader outReader = new BufferedReader(new InputStreamReader(proc.getInputStream()));
             BufferedReader errReader = new BufferedReader(new InputStreamReader(proc.getErrorStream()))) {

            String line;
            while ((line = outReader.readLine()) != null) out.append(line);
            while ((line = errReader.readLine()) != null) err.append(line);
        }

        int exitCode = proc.waitFor();
        if (exitCode != 0) {
            throw new RuntimeException("Python fetcher failed: " + err);
        }

        return parseOhlcvJson(out.toString(), symbol, interval);
    }

    private List<EquityOhlcv> parseOhlcvJson(String json, String symbol, String interval)
            throws Exception {

        JsonNode root = objectMapper.readTree(json);
        List<EquityOhlcv> result = new ArrayList<>();

        for (JsonNode row : root) {
            try {
                EquityOhlcv bar = EquityOhlcv.builder()
                        .symbol(symbol)
                        .ts(Instant.parse(row.get("ts").asText()))
                        .interval(interval)
                        .open(new BigDecimal(row.get("open").asText()))
                        .high(new BigDecimal(row.get("high").asText()))
                        .low(new BigDecimal(row.get("low").asText()))
                        .close(new BigDecimal(row.get("close").asText()))
                        .volume(row.get("volume").asLong())
                        .adjClose(row.has("adj_close") && !row.get("adj_close").isNull()
                                ? new BigDecimal(row.get("adj_close").asText()) : null)
                        .build();
                result.add(bar);
            } catch (Exception e) {
                log.warn("Skipping malformed row for {}: {}", symbol, e.getMessage());
            }
        }
        return result;
    }

    private List<EquityOhlcv> validate(List<EquityOhlcv> rows) {
        List<EquityOhlcv> valid = new ArrayList<>();
        for (EquityOhlcv row : rows) {
            if (row.getOpen() == null || row.getClose() == null
                    || row.getHigh() == null || row.getLow() == null) {
                log.debug("Null OHLC for {} @ {}, skipping", row.getSymbol(), row.getTs());
                continue;
            }
            if (row.getHigh().compareTo(row.getLow()) < 0) {
                log.warn("H < L for {} @ {}, skipping", row.getSymbol(), row.getTs());
                continue;
            }
            if (row.getOpen().compareTo(BigDecimal.ZERO) <= 0) {
                log.warn("Non-positive open for {} @ {}, skipping", row.getSymbol(), row.getTs());
                continue;
            }
            valid.add(row);
        }
        log.debug("Validated {}/{} rows", valid.size(), rows.size());
        return valid;
    }

    private int upsertBatch(List<EquityOhlcv> rows) {
        // Filter already-existing rows
        List<EquityOhlcv> toInsert = rows.stream()
                .filter(r -> !ohlcvRepository.existsBySymbolAndTsAndInterval(r.getSymbol(), r.getTs(), r.getInterval()))
                .toList();
        ohlcvRepository.saveAll(toInsert);
        return toInsert.size();
    }

    public record IngestionResult(String symbol, String status, int rowsInserted, String message) {
        static IngestionResult success(String symbol, int rows) {
            return new IngestionResult(symbol, "success", rows, null);
        }
        static IngestionResult empty(String symbol) {
            return new IngestionResult(symbol, "empty", 0, "No data returned");
        }
        static IngestionResult error(String symbol, String msg) {
            return new IngestionResult(symbol, "error", 0, msg);
        }
    }
}
