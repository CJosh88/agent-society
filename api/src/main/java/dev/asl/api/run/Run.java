package dev.asl.api.run;

import java.time.Instant;
import java.util.UUID;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import org.springframework.data.domain.Persistable;

/** Ids are assigned by the engine, so isNew() is always true: save() must insert, never merge. */
@Entity
@Table(name = "runs")
class Run implements Persistable<UUID> {

	@Id
	UUID id;
	String experiment;
	String scenario;
	String condition;
	/** The population label (llama-3.1-8b, mix_early, ...); the column keeps its v0.3 name. */
	String model;
	/** The world seed. */
	long seed;
	String promptVersion;
	String engineVersion;
	boolean pilot;
	Instant startedAt;
	Instant endedAt;
	Double accuracy;
	int ratedCount;
	int parseFailures;
	int truncations;
	int llmCallCount;
	int probeCount;
	int recognisedSample;
	Instant createdAt;

	@Override
	public UUID getId() {
		return id;
	}

	@Override
	public boolean isNew() {
		return true;
	}
}
