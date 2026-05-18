package com.msrap.repository;

import com.msrap.model.RegimeState;
import com.msrap.model.RegimeStateId;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;

@Repository
public interface RegimeStateRepository extends JpaRepository<RegimeState, RegimeStateId> {

    List<RegimeState> findBySymbolOrderByTsAsc(String symbol);

    List<RegimeState> findBySymbolAndTsBetweenOrderByTsAsc(String symbol, Instant from, Instant to);

    @Query("SELECT r FROM RegimeState r WHERE r.symbol = :symbol ORDER BY r.ts DESC LIMIT 1")
    Optional<RegimeState> findLatest(@Param("symbol") String symbol);
}
