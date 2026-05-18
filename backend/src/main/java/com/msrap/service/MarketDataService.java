package com.msrap.service;

import com.msrap.model.EquityOhlcv;
import com.msrap.model.Instrument;
import com.msrap.repository.EquityOhlcvRepository;
import com.msrap.repository.InstrumentRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.List;
import java.util.Optional;

@Slf4j
@Service
@RequiredArgsConstructor
public class MarketDataService {

    private final EquityOhlcvRepository ohlcvRepository;
    private final InstrumentRepository instrumentRepository;

    public List<Instrument> getAllInstruments() {
        return instrumentRepository.findByIsActiveTrue();
    }

    public Optional<Instrument> getInstrument(String symbol) {
        return instrumentRepository.findById(symbol);
    }

    public List<EquityOhlcv> getOhlcv(String symbol, String interval, int days) {
        Instant from = Instant.now().minus(days, ChronoUnit.DAYS);
        return ohlcvRepository.findSince(symbol, interval, from);
    }

    public List<EquityOhlcv> getOhlcvRange(String symbol, String interval,
                                             Instant from, Instant to) {
        return ohlcvRepository.findBySymbolAndIntervalAndTsBetweenOrderByTsAsc(symbol, interval, from, to);
    }

    public Optional<EquityOhlcv> getLatestBar(String symbol, String interval) {
        return ohlcvRepository.findLatestBySymbolAndInterval(symbol, interval);
    }

    public List<String> getAvailableSymbols() {
        return instrumentRepository.findByIsActiveTrue()
                .stream()
                .map(Instrument::getSymbol)
                .toList();
    }

    public List<Instrument> getByAssetClass(String assetClass) {
        return instrumentRepository.findByAssetClass(assetClass);
    }

    public List<Instrument> getBySector(String sector) {
        return instrumentRepository.findBySector(sector);
    }
}
