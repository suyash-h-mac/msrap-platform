package com.msrap.model;

import jakarta.persistence.*;
import lombok.*;
import java.time.Instant;

@Entity
@Table(name = "instruments")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class Instrument {

    @Id
    @Column(nullable = false, length = 32)
    private String symbol;

    @Column(length = 128)
    private String name;

    @Column(length = 16)
    private String exchange;

    @Column(name = "asset_class", length = 16)
    private String assetClass;

    @Column(length = 64)
    private String sector;

    @Column(name = "is_active")
    private Boolean isActive;

    @Column(name = "created_at")
    private Instant createdAt;
}
