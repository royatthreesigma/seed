"use client";

import axios from "axios";

/**
 * README:
 * This module exports a pre-configured Axios instance for making API requests.
 * It includes an interceptor that automatically attaches an authentication token
 * to each request if the user is signed in.
 * 
 * Whether to enable this behaviour depends on your need, and if you have Clerk
 * setup in your application. With Shippable, Clerk is the default auth provider, 
 * and should work out of the box. To enable it you will have to provide Clerk
 * key(s) in your environment variables, wrap your app with <ClerkProvider>,
 * and mount the <AxiosAuthProvider> near the root of your app. These should be
 * available in the root layout.tsx and commented out.
 * 
 * Uncomment the code below to enable this functionality.
 * 
 * NOTE:
 * If you do not wish to use Clerk, or do not need auth tokens attached
 * to your API requests, you can simply use the default axiosInstance exported at the bottom.
 * 
 * 
 * 
 * KNOW:
 * By using axios this way, we are making the opinionated choice to not use Next.js as
 * a backend for API routes, but rather to call the backend API directly from the frontend.

import type { PropsWithChildren } from "react";
import { useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
export const axiosInstance = axios.create({
	baseURL: process.env.NEXT_PUBLIC_API_URL,
});

// Module-scoped token getter that the interceptor will call
let getTokenFn: null | (() => Promise<string | null>) = null;
let authReadyResolve: (() => void) | null = null;
const authReadyPromise = new Promise<void>((resolve) => {
	authReadyResolve = resolve;
});

// Install interceptor immediately (runs when module loads)
axiosInstance.interceptors.request.use(async (config) => {
	// Wait for auth to be initialized before proceeding
	await authReadyPromise;
	
	if (getTokenFn) {
		const token = await getTokenFn();
		if (token) {
			config.headers = config.headers ?? {};
			config.headers.Authorization = `Bearer ${token}`;
		}
	}
	return config;
});

export function markAuthReady() {
	if (authReadyResolve) {
		authReadyResolve();
		authReadyResolve = null;
	}
}

 * Mount once near the root (inside <ClerkProvider />).
 * This wires Clerk -> Axios so you can keep calling:
 *   await axiosInstance.get<T>(url)
export function AxiosAuthProvider({ children }: PropsWithChildren) {
	const { getToken, isLoaded, isSignedIn } = useAuth();
	
	useEffect(() => {
		if (!isLoaded) return;
		
		// Set up token getter
		getTokenFn = async () => (isSignedIn ? await getToken() : null);
		
		// Signal that auth is ready - this unblocks any pending requests
		markAuthReady();
		
		// Cleanup on unmount
		return () => {
			getTokenFn = null;
		};
	}, [getToken, isLoaded, isSignedIn]);
	
	return children;
}

export default axiosInstance;
*/

// Axios instance setup (normal/default)
const axiosInstance = axios.create({
	baseURL: process.env.NEXT_PUBLIC_API_URL,
});

// Add a request interceptor (include auth token if available)
axiosInstance.interceptors.request.use(
	async (config) => {
		return config;
	},
	(error) => {
		return Promise.reject(error);
	},
);

export default axiosInstance;
