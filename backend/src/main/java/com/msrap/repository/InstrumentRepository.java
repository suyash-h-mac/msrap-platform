package com.msrap.repository;

import com.msrap.model.Instrument;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;
import java.util.List;

@Repository
public interface InstrumentRepository extends JpaRepository<Instrument, String> {
    List<Instrument> findByIsActiveTrue();
    List<Instrument> findByAssetClass(String assetClass);
    List<Instrument> findBySector(String sector);
}
