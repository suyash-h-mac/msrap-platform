package com.msrap.controller;

import com.msrap.scheduler.MarketScheduler;
import com.msrap.service.IngestionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/ingestion")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class IngestionController {

    private final IngestionService ingestionService;
    private final MarketScheduler scheduler;

    @PostMapping("/ingest/{symbol}")
    public ResponseEntity<Map<String, Object>> ingestSymbol(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "1d") String interval) {
        IngestionService.IngestionResult result = ingestionService.ingestSymbol(symbol, interval);
        return ResponseEntity.ok(Map.of(
                "symbol", result.symbol(),
                "status", result.status(),
                "rowsInserted", result.rowsInserted(),
                "message", result.message() != null ? result.message() : ""
        ));
    }

    @PostMapping("/backfill")
    public ResponseEntity<String> triggerBackfill() {
        scheduler.backfillAll();
        return ResponseEntity.ok("Backfill started for all configured symbols");
    }

    @PostMapping("/ingest/batch")
    public ResponseEntity<List<Map<String, Object>>> ingestBatch(
            @RequestBody List<String> symbols,
            @RequestParam(defaultValue = "1d") String interval) {
        List<Map<String, Object>> results = symbols.stream()
                .map(s -> {
                    IngestionService.IngestionResult r = ingestionService.ingestSymbol(s, interval);
                    return Map.<String, Object>of(
                            "symbol", r.symbol(),
                            "status", r.status(),
                            "rowsInserted", r.rowsInserted()
                    );
                })
                .toList();
        return ResponseEntity.ok(results);
    }
}
