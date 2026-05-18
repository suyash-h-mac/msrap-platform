package com.msrap.repository;

import com.msrap.model.FactorLoading;
import com.msrap.model.FactorLoadingId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface FactorLoadingRepository extends JpaRepository<FactorLoading, FactorLoadingId> {

    List<FactorLoading> findBySymbolAndWindowDaysOrderByTsAsc(String symbol, Short windowDays);

    @Query("SELECT f FROM FactorLoading f WHERE f.symbol = :symbol AND f.windowDays = :window ORDER BY f.ts DESC LIMIT 1")
    Optional<FactorLoading> findLatest(@Param("symbol") String symbol, @Param("window") Short windowDays);

    List<FactorLoading> findBySymbolAndWindowDaysAndTsBetweenOrderByTsAsc(
            String symbol, Short windowDays, Instant from, Instant to);
}
