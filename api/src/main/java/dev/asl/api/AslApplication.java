package dev.asl.api;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.context.properties.ConfigurationPropertiesScan;

@SpringBootApplication
@ConfigurationPropertiesScan
public class AslApplication {

	public static void main(String[] args) {
		SpringApplication.run(AslApplication.class, args);
	}

}
