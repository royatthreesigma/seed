"use client";

import { useEffect, useState } from "react";
import axiosInstance from "@/services/axios";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { CheckCircle2, XCircle, AlertTriangle, RefreshCw, Server, Lock } from "lucide-react";
import { HealthStatus } from "@/types/health";

export default function ReservedPage() {
	const [unauthenticatedHealth, setUnauthenticatedHealth] = useState<HealthStatus | null>(null);
	const [authenticatedHealth, setAuthenticatedHealth] = useState<HealthStatus | null>(null);
	const [loading, setLoading] = useState(true);
	const [refreshing, setRefreshing] = useState(false);

	const fetchHealthChecks = async (isRefresh = false) => {
		if (isRefresh) {
			setRefreshing(true);
		} else {
			setLoading(true);
		}

		// Unauthenticated health check
		try {
			const response = await axiosInstance.get("/reserved/health/");
			setUnauthenticatedHealth({ status: response.data.status });
		} catch (error: any) {
			setUnauthenticatedHealth({
				status: "Failed",
				error: error.response?.data?.detail || error.message,
			});
		}

		// Authenticated health check
		try {
			const response = await axiosInstance.get("/reserved/authenticated-health/");
			setAuthenticatedHealth({ status: response.data.status });
		} catch (error: any) {
			setAuthenticatedHealth({
				status: "Failed",
				error: error.response?.data?.detail || error.message,
			});
		}

		setLoading(false);
		setRefreshing(false);
	};

	useEffect(() => {
		fetchHealthChecks();
	}, []);

	const getStatusIcon = (health: HealthStatus | null) => {
		if (!health) return <AlertTriangle className="h-5 w-5 text-muted-foreground" />;
		if (health.error) return <XCircle className="h-5 w-5 text-destructive" />;
		return <CheckCircle2 className="h-5 w-5 text-green-500" />;
	};

	const getStatusBadge = (health: HealthStatus | null) => {
		if (!health) return <Badge variant="secondary">Unknown</Badge>;
		if (health.error) return <Badge variant="destructive">Error</Badge>;
		return (
			<Badge variant="default" className="bg-green-500 hover:bg-green-600">
				Healthy
			</Badge>
		);
	};

	if (loading) {
		return (
			<div className="flex items-center justify-center min-h-screen p-4">
				<div className="text-center space-y-4">
					<RefreshCw className="h-8 w-8 animate-spin mx-auto text-muted-foreground" />
					<p className="text-muted-foreground">Loading health checks...</p>
				</div>
			</div>
		);
	}

	return (
		<div className="h-screen overflow-y-auto">
			<div className="container mx-auto p-6 max-w-4xl space-y-6">
				{/* Header */}
				<div className="space-y-2">
					<h1 className="text-3xl font-bold tracking-tight">API Health Status</h1>
					<p className="text-muted-foreground">Monitor the health and availability of your API endpoints</p>
				</div>

				<Separator />

				{/* Health Check Cards */}
				<div className="grid gap-6 md:grid-cols-2">
					{/* Unauthenticated Health Check */}
					<Card>
						<CardHeader>
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<Server className="h-5 w-5 text-muted-foreground" />
									<CardTitle>Public Endpoint</CardTitle>
								</div>
								{getStatusIcon(unauthenticatedHealth)}
							</div>
							<CardDescription>Unauthenticated health check</CardDescription>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="flex items-center justify-between">
								<span className="text-sm font-medium">Status</span>
								{getStatusBadge(unauthenticatedHealth)}
							</div>

							{unauthenticatedHealth?.status && (
								<div className="space-y-1">
									<span className="text-sm font-medium">Response</span>
									<p className="text-sm text-muted-foreground">{unauthenticatedHealth.status}</p>
								</div>
							)}

							{unauthenticatedHealth?.error && (
								<Alert variant="destructive">
									<AlertDescription className="text-sm">{unauthenticatedHealth.error}</AlertDescription>
								</Alert>
							)}
						</CardContent>
					</Card>

					{/* Authenticated Health Check */}
					<Card>
						<CardHeader>
							<div className="flex items-center justify-between">
								<div className="flex items-center gap-2">
									<Lock className="h-5 w-5 text-muted-foreground" />
									<CardTitle>Protected Endpoint</CardTitle>
								</div>
								{getStatusIcon(authenticatedHealth)}
							</div>
							<CardDescription>Authenticated health check</CardDescription>
						</CardHeader>
						<CardContent className="space-y-4">
							<div className="flex items-center justify-between">
								<span className="text-sm font-medium">Status</span>
								{getStatusBadge(authenticatedHealth)}
							</div>

							{authenticatedHealth?.status && (
								<div className="space-y-1">
									<span className="text-sm font-medium">Response</span>
									<p className="text-sm text-muted-foreground">{authenticatedHealth.status}</p>
								</div>
							)}

							{authenticatedHealth?.error && (
								<Alert variant="destructive">
									<AlertDescription className="text-sm">{authenticatedHealth.error}</AlertDescription>
								</Alert>
							)}
						</CardContent>
					</Card>
				</div>

				{/* Refresh Button */}
				<div className="flex justify-center pt-4">
					<Button onClick={() => fetchHealthChecks(true)} disabled={refreshing} variant="outline" size="lg">
						<RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? "animate-spin" : ""}`} />
						{refreshing ? "Refreshing..." : "Refresh Health Checks"}
					</Button>
				</div>

				{/* Info Card */}
				<Card className="border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950">
					<CardHeader>
						<CardTitle className="text-base">About Health Checks</CardTitle>
					</CardHeader>
					<CardContent className="text-sm text-muted-foreground space-y-2">
						<p>
							<strong>Public Endpoint:</strong> Tests the basic API availability without authentication.
						</p>
						<p>
							<strong>Protected Endpoint:</strong> Tests authenticated access and validates your credentials.
						</p>
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
