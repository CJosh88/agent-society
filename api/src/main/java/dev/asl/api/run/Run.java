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
	String model;
	long seed;
	String promptVersion;
	String engineVersion;
	boolean pilot;
	Instant startedAt;
	Instant endedAt;
	boolean focalHelped;
	boolean earlyHelp;
	Integer focalHelpTick;
	int decisionCount;
	int parseFailures;
	int truncations;
	int llmCallCount;
	Boolean recognized;
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
