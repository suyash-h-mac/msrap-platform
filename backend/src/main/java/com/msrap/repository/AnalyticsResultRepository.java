package com.msrap.repository;

import com.msrap.model.AnalyticsResult;
import com.msrap.model.AnalyticsResultId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.Instant;
import java.util.List;

@Repository
public interface AnalyticsResultRepository extends JpaRepository<AnalyticsResult, AnalyticsResultId> {

    List<AnalyticsResult> findBySymbolAndModuleOrderByTsDesc(String symbol, String module);

    List<AnalyticsResult> findBySymbolAndModuleAndMetricOrderByTsAsc(
            String symbol, String module, String metric);

    @Query("SELECT a FROM AnalyticsResult a WHERE a.symbol = :symbol AND a.module = :module AND a.ts >= :from ORDER BY a.ts ASC")
    List<AnalyticsResult> findSince(@Param("symbol") String symbol,
                                    @Param("module") String module,
                                    @Param("from") Instant from);

    @Query("SELECT a FROM AnalyticsResult a WHERE a.symbol = :symbol AND a.module = :module ORDER BY a.ts DESC LIMIT :n")
    List<AnalyticsResult> findLatestN(@Param("symbol") String symbol,
                                      @Param("module") String module,
                                      @Param("n") int n);
}
