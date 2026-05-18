package com.msrap.controller;

import com.msrap.model.EquityOhlcv;
import com.msrap.model.Instrument;
import com.msrap.service.MarketDataService;
import lombok.RequiredArgsConstructor;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.Instant;
import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/market")
@RequiredArgsConstructor
@CrossOrigin(origins = "*")
public class MarketController {

    private final MarketDataService marketDataService;

    @GetMapping("/instruments")
    public ResponseEntity<List<Instrument>> getAllInstruments() {
        return ResponseEntity.ok(marketDataService.getAllInstruments());
    }

    @GetMapping("/instruments/{symbol}")
    public ResponseEntity<Instrument> getInstrument(@PathVariable String symbol) {
        return marketDataService.getInstrument(symbol)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/ohlcv/{symbol}")
    public ResponseEntity<List<EquityOhlcv>> getOhlcv(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "1d") String interval,
            @RequestParam(defaultValue = "365") int days) {
        return ResponseEntity.ok(marketDataService.getOhlcv(symbol, interval, days));
    }

    @GetMapping("/ohlcv/{symbol}/range")
    public ResponseEntity<List<EquityOhlcv>> getOhlcvRange(
            @PathVariable String symbol,
            @RequestParam String interval,
            @RequestParam Instant from,
            @RequestParam Instant to) {
        return ResponseEntity.ok(marketDataService.getOhlcvRange(symbol, interval, from, to));
    }

    @GetMapping("/ohlcv/{symbol}/latest")
    public ResponseEntity<EquityOhlcv> getLatest(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "1d") String interval) {
        return marketDataService.getLatestBar(symbol, interval)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/symbols")
    public ResponseEntity<List<String>> getSymbols() {
        return ResponseEntity.ok(marketDataService.getAvailableSymbols());
    }

    @GetMapping("/instruments/sector/{sector}")
    public ResponseEntity<List<Instrument>> getBySector(@PathVariable String sector) {
        return ResponseEntity.ok(marketDataService.getBySector(sector));
    }
}
