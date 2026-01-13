"use client";

import { useEffect, useState } from "react";
import { healthService } from "@/services/health";
import type { HealthCheckResult } from "@/types/health";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";

export default function HealthPage() {
	const [health, setHealth] = useState<HealthCheckResult>({
		anonymous: null,
		authenticated: null,
	});
	const [loading, setLoading] = useState({
		anonymous: false,
		authenticated: false,
	});

	const checkAnonymousHealth = async () => {
		setLoading((prev) => ({ ...prev, anonymous: true }));
		try {
			const data = await healthService.checkAnonymous();
			setHealth((prev) => ({ ...prev, anonymous: data }));
		} catch (error) {
			setHealth((prev) => ({
				...prev,
				anonymous: {
					status: "error",
					error: "Failed to connect to API",
				},
			}));
		} finally {
			setLoading((prev) => ({ ...prev, anonymous: false }));
		}
	};

	const checkAuthenticatedHealth = async () => {
		setLoading((prev) => ({ ...prev, authenticated: true }));
		try {
			const data = await healthService.checkAuthenticated();
			setHealth((prev) => ({ ...prev, authenticated: data }));
		} catch (error: any) {
			setHealth((prev) => ({
				...prev,
				authenticated: {
					status: "error",
					error: error?.response?.data?.status || "Failed to connect to authenticated endpoint",
				},
			}));
		} finally {
			setLoading((prev) => ({ ...prev, authenticated: false }));
		}
	};

	useEffect(() => {
		checkAnonymousHealth();
		checkAuthenticatedHealth();
	}, []);

	const renderStatus = (statusData: { status: string; error?: string } | null, isLoading: boolean) => {
		if (isLoading) {
			return (
				<div className="flex items-center gap-2">
					<Spinner size="sm" />
					<span className="text-sm text-muted-foreground">Checking...</span>
				</div>
			);
		}

		if (!statusData) {
			return <span className="text-sm text-muted-foreground">Not checked yet</span>;
		}

		if (statusData.error) {
			return (
				<div className="flex items-center gap-2">
					<span className="h-3 w-3 rounded-full bg-destructive"></span>
					<span className="text-sm text-destructive">{statusData.error}</span>
				</div>
			);
		}

		return (
			<div className="flex items-center gap-2">
				<span className="h-3 w-3 rounded-full bg-green-500"></span>
				<span className="text-sm text-green-600">{statusData.status}</span>
			</div>
		);
	};

	return (
		<div className="flex min-h-screen items-center justify-center bg-background p-4">
			<div className="w-full max-w-2xl space-y-4">
				<Card>
					<CardHeader>
						<CardTitle>API Health Check</CardTitle>
					</CardHeader>
					<CardContent className="space-y-6">
						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<h3 className="font-medium">Anonymous Endpoint</h3>
								<Button size="sm" variant="outline" onClick={checkAnonymousHealth} disabled={loading.anonymous}>
									Refresh
								</Button>
							</div>
							<div className="rounded-lg border bg-muted/50 p-4">
								<div className="flex items-center justify-between">
									<span className="text-sm font-medium text-muted-foreground">
										Endpoint: <code className="text-xs">/health/</code>
									</span>
									{renderStatus(health.anonymous, loading.anonymous)}
								</div>
							</div>
						</div>

						<div className="space-y-2">
							<div className="flex items-center justify-between">
								<h3 className="font-medium">Authenticated Endpoint</h3>
								<Button size="sm" variant="outline" onClick={checkAuthenticatedHealth} disabled={loading.authenticated}>
									Refresh
								</Button>
							</div>
							<div className="rounded-lg border bg-muted/50 p-4">
								<div className="flex items-center justify-between">
									<span className="text-sm font-medium text-muted-foreground">
										Endpoint: <code className="text-xs">/authenticated-health/</code>
									</span>
									{renderStatus(health.authenticated, loading.authenticated)}
								</div>
							</div>
						</div>
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
