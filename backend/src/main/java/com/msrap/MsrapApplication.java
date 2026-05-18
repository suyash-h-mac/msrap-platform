package com.msrap;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.scheduling.annotation.EnableScheduling;

import com.msrap.config.IngestionProperties;

@SpringBootApplication
@EnableScheduling
@EnableConfigurationProperties(IngestionProperties.class)
public class MsrapApplication {
    public static void main(String[] args) {
        SpringApplication.run(MsrapApplication.class, args);
    }
}
