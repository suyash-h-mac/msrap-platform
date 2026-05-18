package com.msrap.repository;

import com.msrap.model.EquityOhlcv;
import com.msrap.model.EquityOhlcvId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface EquityOhlcvRepository extends JpaRepository<EquityOhlcv, EquityOhlcvId> {

    List<EquityOhlcv> findBySymbolAndIntervalOrderByTsAsc(String symbol, String interval);

    List<EquityOhlcv> findBySymbolAndIntervalAndTsBetweenOrderByTsAsc(
            String symbol, String interval, Instant from, Instant to);

    @Query("SELECT e FROM EquityOhlcv e WHERE e.symbol = :symbol AND e.interval = :interval ORDER BY e.ts DESC LIMIT 1")
    Optional<EquityOhlcv> findLatestBySymbolAndInterval(
            @Param("symbol") String symbol, @Param("interval") String interval);

    @Query(value = """
            SELECT symbol, ts, open, high, low, close, volume, adj_close, interval
            FROM equity_ohlcv
            WHERE symbol = :symbol AND interval = :interval AND ts >= :from
            ORDER BY ts ASC
            """, nativeQuery = true)
    List<EquityOhlcv> findSince(@Param("symbol") String symbol,
                                @Param("interval") String interval,
                                @Param("from") Instant from);

    @Query(value = """
            SELECT time_bucket('1 week', ts) AS ts,
                   symbol, interval,
                   first(open, ts)  AS open,
                   max(high)        AS high,
                   min(low)         AS low,
                   last(close, ts)  AS close,
                   sum(volume)      AS volume,
                   last(adj_close, ts) AS adj_close
            FROM equity_ohlcv
            WHERE symbol = :symbol AND interval = '1d'
              AND ts >= :from
            GROUP BY time_bucket('1 week', ts), symbol, interval
            ORDER BY ts ASC
            """, nativeQuery = true)
    List<EquityOhlcv> findWeeklyAggregated(@Param("symbol") String symbol,
                                            @Param("from") Instant from);

    boolean existsBySymbolAndTsAndInterval(String symbol, Instant ts, String interval);
}
