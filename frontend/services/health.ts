import axiosInstance from "@/lib/axios";
import type { HealthStatus } from "@/types/health";

export const healthService = {
	checkAnonymous: async (): Promise<HealthStatus> => {
		const response = await axiosInstance.get<{ status: string }>("/health/");
		return response.data;
	},

	checkAuthenticated: async (): Promise<HealthStatus> => {
		const response = await axiosInstance.get<{ status: string }>(
			"/authenticated-health/"
		);
		return response.data;
	},
};
