export interface HealthStatus {
	status: string;
	error?: string;
}

export interface HealthCheckResult {
	anonymous: HealthStatus | null;
	authenticated: HealthStatus | null;
}