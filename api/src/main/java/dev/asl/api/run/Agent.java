package dev.asl.api.run;

import java.util.Map;
import java.util.UUID;

import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;

import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import org.springframework.data.domain.Persistable;

@Entity
@Table(name = "agents")
@IdClass(AgentId.class)
class Agent implements Persistable<AgentId> {

	@Id
	UUID runId;
	@Id
	String agentId;
	String name;
	String role;
	@JdbcTypeCode(SqlTypes.JSON)
	Map<String, Object> persona;

	@Override
	public AgentId getId() {
		return new AgentId(runId, agentId);
	}

	@Override
	public boolean isNew() {
		return true;
	}
}
